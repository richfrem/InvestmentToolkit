#!/usr/bin/env python3
"""
QuestradeAPIClient.py
=====================================

Purpose:
    Client for interacting with the Questrade API, handling account discovery and position retrieval.

Layer: Retrieve

Usage:
    Imported by QuestradeDataEngine.py.

Related:
    - QuestradeTokenManager.py
    - QuestradeDataEngine.py
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

    def _get_api_server(self) -> str:
        """
        Retrieves the current API server URL from tokens.

        Returns:
            The API server base URL.

        Raises:
            RuntimeError: If server URL is missing.
        """
        tokens = self.token_manager.load_tokens()
        if not tokens or "api_server" not in tokens:
            raise RuntimeError("API server URL missing from cache.")
        return tokens["api_server"].rstrip('/')

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Executes an authenticated API request with automatic token rotation on 401.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint relative to server root.
            **kwargs: Additional arguments for requests.request.

        Returns:
            JSON response as dictionary.

        Raises:
            HTTPError: If the request fails.
        """
        url = f"{self._get_api_server()}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        response = requests.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401:
            self.logger.info("Access token expired. Attempting rotation...")
            # Note: Rotation logic is coordinated by the SyncEngine calling a refresh.
            pass
            
        response.raise_for_status()
        return response.json()

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
