#!/usr/bin/env python3
"""
QuestradeAPIClient.py (Python Utility)
=====================================

Purpose:
    Low-level HTTP client for interacting with the Questrade API. 
    Handles account discovery, position retrieval, and automatic OAuth2 token rotation.

Layer: Backend / Utils / API Client

Usage Examples:
    token_manager = QuestradeTokenManager(cache_dir="path/to/cache")
    client = QuestradeAPIClient(token_manager)
    positions = client.get_all_positions()

Key Functions:
    - get_all_positions() - Discovers all linked accounts and aggregates every holding into a unified list
    - get_all_balances() - Aggregates cash balances (CAD/USD) across all brokerage accounts
    - refresh_tokens() - Internal utility for rotating the refresh token via the Questrade OAuth2 endpoint
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from .QuestradeTokenManager import QuestradeTokenManager

class QuestradeAPIClient:
    """
    Client for interacting with the Questrade API.
    Handles account discovery, position fetching, and automatic token rotation.
    Implements ADR 015/017/018.
    """

    def __init__(self, token_manager: QuestradeTokenManager):
        """
        Initializes the client with a token manager.

        Args:
            token_manager: Instance of QuestradeTokenManager for auth.
        """
        self.token_manager = token_manager
        self.logger = logging.getLogger(__name__)

    def _get_headers(self) -> Dict[str, str]:
        """
        Loads valid tokens and returns authorization headers.

        Returns:
            Dictionary with Bearer token and Content-Type.
        
        Raises:
            RuntimeError: If tokens are missing.
        """
        tokens = self.token_manager.load_tokens()
        if not tokens or "access_token" not in tokens:
            raise RuntimeError("No valid tokens found. Please seed the refresh token first.")
        
        return {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }

    def refresh_tokens(self) -> Dict[str, Any]:
        """
        Refreshes tokens using the current refresh token.
        Implements ADR 015.

        Returns:
            The new token dictionary.

        Raises:
            RuntimeError: If refresh fails.
        """
        tokens = self.token_manager.load_tokens()
        if not tokens or "refresh_token" not in tokens:
            raise RuntimeError("No refresh token available to rotate.")

        refresh_token = tokens["refresh_token"]
        url = f"https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token={refresh_token}"
        
        self.logger.info("Rotating Questrade tokens...")
        response = requests.post(url)
        
        if not response.ok:
            # Defensive: handle non-JSON error bodies
            try:
                error_data = response.json()
            except ValueError:
                error_data = {"status_code": response.status_code, "body": response.text}
            raise RuntimeError(f"Token rotation failed: {error_data}")

        try:
            new_tokens = response.json()
        except ValueError:
            # Unexpected non-JSON success response
            raise RuntimeError(f"Token rotation succeeded with non-JSON body: status={response.status_code}, body={response.text}")

        self.token_manager.save_tokens(new_tokens)
        self.logger.info("Tokens rotated successfully.")
        return new_tokens

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Executes an authenticated API request with automatic token rotation.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint relative to server root.
            **kwargs: Additional arguments for requests.request.

        Returns:
            JSON response as dictionary.

        Raises:
            HTTPError: If the request fails.
        """
        # Ensure we have valid session data (ADR 015)
        tokens = self.token_manager.load_tokens()
        if not tokens or "access_token" not in tokens or "api_server" not in tokens:
            self.logger.info("Session incomplete. Attempting initial rotation...")
            tokens = self.refresh_tokens()

        url = f"{tokens['api_server'].rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401:
            self.logger.info("Access token expired (401). Attempting rotation...")
            tokens = self.refresh_tokens()
            
            # Retry once with new tokens
            url = f"{tokens['api_server'].rstrip('/')}/{endpoint.lstrip('/')}"
            headers["Authorization"] = f"Bearer {tokens['access_token']}"
            response = requests.request(method, url, headers=headers, **kwargs)
            
        # Raise detailed errors for non-JSON or bad responses
        try:
            response.raise_for_status()
        except requests.HTTPError as he:
            # Attempt to include response body for easier debugging
            body = None
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise RuntimeError(f"HTTP error during request: {he}, status={response.status_code}, body={body}")

        try:
            return response.json()
        except ValueError:
            raise RuntimeError(f"Non-JSON response from Questrade: status={response.status_code}, body={response.text}")

    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Retrieves all accounts associated with the profile.

        Returns:
            List of account dictionaries.
        """
        data = self._request("GET", "v1/accounts")
        return data.get("accounts", [])

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves current positions for a specific account.

        Args:
            account_id: The Questrade account number.

        Returns:
            List of position dictionaries.
        """
        data = self._request("GET", f"v1/accounts/{account_id}/positions")
        return data.get("positions", [])

    def get_balances(self, account_id: str) -> Dict[str, Any]:
        """
        Retrieves current balances (cash) for a specific account.

        Args:
            account_id: The Questrade account number.

        Returns:
            Dictionary containing combined, per-currency balances.
        """
        return self._request("GET", f"v1/accounts/{account_id}/balances")

    def get_all_balances(self) -> List[Dict[str, Any]]:
        """
        Discover all accounts and aggregate all cash balances.

        Returns:
            List of balance dictionaries from all accounts.
        """
        all_balances = []
        accounts = self.get_accounts()
        for account in accounts:
            account_id = account["number"]
            self.logger.info(f"Fetching balances for account {account_id} ({account['type']})")
            balances = self.get_balances(account_id)
            # Annotate with account info
            balances["_account_id"] = account_id
            balances["_account_type"] = account["type"]
            all_balances.append(balances)
        return all_balances

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        Discover all accounts and aggregate all positions into a flat list.

        Returns:
            Flat list of positions from all accounts with account metadata.
        """
        all_positions = []
        accounts = self.get_accounts()
        
        for account in accounts:
            account_id = account["number"]
            self.logger.info(f"Fetching positions for account {account_id} ({account['type']})")
            positions = self.get_positions(account_id)
            # Annotate positions with account info for auditing
            for pos in positions:
                pos["_account_id"] = account_id
                pos["_account_type"] = account["type"]
            all_positions.extend(positions)
            
        return all_positions
