#!/usr/bin/env python3
"""
PortfolioAggregator.py
=====================================

Purpose:
    Handles aggregation of Questrade positions into the unified portfolio.json format.

Layer: Retrieve

Usage:
    Imported by QuestradeDataEngine.py or used standalone in scripts.

Related:
    - QuestradeDataEngine.py
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

class PortfolioAggregator:
    """
    Handles aggregation of Questrade positions into the unified portfolio.json format.
    Implements ADR 018.
    """

    def __init__(self, output_path: str):
        """
        Initializes the aggregator with a target output path.

        Args:
            output_path: Path to the target portfolio.json file.
        """
        self.output_path = output_path

    def normalize_symbol(self, symbol: str) -> str:
        """
        Removes exchange suffixes for consistency (e.g. AAPL.US -> AAPL).

        Args:
            symbol: The raw ticker symbol from Questrade.

        Returns:
            The normalized ticker symbol.
        """
        if "." in symbol:
            return symbol.split(".")[0]
        return symbol

    def aggregate_positions(self, positions: List[Dict[str, Any]], balances: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Aggregates multiple positions of the same ticker across accounts.
        Computes total shares and keeps price data. Also aggregates cash balances.

        Args:
            positions: List of raw position dictionaries from Questrade.
            balances: List of balance dictionaries from Questrade accounts.

        Returns:
            List of aggregated holding dictionaries in portfolio.json format.
        """
        aggregated: Dict[str, Dict[str, Any]] = {}

        for pos in positions:
            raw_symbol = pos.get("symbol", "")
            if not raw_symbol:
                continue
                
            symbol = self.normalize_symbol(raw_symbol)
            shares = float(pos.get("openQuantity") or 0)
            price = float(pos.get("currentPrice") or 0)
            book_price = float(pos.get("averageEntryPrice") or 0) or None
            
            if symbol in aggregated:
                old_shares = aggregated[symbol]["shares"]
                old_book   = aggregated[symbol].get("book_price") or 0.0
                new_book   = book_price or 0.0
                total_shares = old_shares + shares

                aggregated[symbol]["shares"] = total_shares
                aggregated[symbol]["price"] = price

                # Weighted-average book price across accounts
                if old_book > 0 and new_book > 0:
                    aggregated[symbol]["book_price"] = (
                        (old_shares * old_book + shares * new_book) / total_shares
                    )
                elif new_book > 0:
                    aggregated[symbol]["book_price"] = new_book
                # else: keep whatever we already have
            else:
                aggregated[symbol] = {
                    "symbol": symbol,
                    "shares": shares,
                    "price": price,
                    "book_price": book_price,
                    "sector": "Other",       # Placeholder: Questrade doesn't provide sectors via positions
                    "industry": "Other",     # Placeholder
                    "last_updated": datetime.now().isoformat()
                }

        # Aggregate Cash Balances (USD)
        if balances:
            total_usd_cash = 0.0
            for account_balance in balances:
                # 'perCurrencyBalances' contains the actual cash
                curr_balances = account_balance.get("perCurrencyBalances", [])
                for cb in curr_balances:
                    if cb.get("currency") == "USD":
                        total_usd_cash += float(cb.get("cash") or 0)
            
            if total_usd_cash > 0:
                # Create or update USD_CASH entry
                # We treat shares as the total cash amount, and price as 1.0
                symbol = "USD_CASH"
                aggregated[symbol] = {
                    "symbol": symbol,
                    "shares": total_usd_cash,
                    "price": 1.0,
                    "book_price": 1.0,
                    "name": "USD Cash",
                    "sector": "CASH",
                    "industry": "CASH",
                    "last_updated": datetime.now().isoformat()
                }

        # Filter out zero share positions
        return [data for data in aggregated.values() if data["shares"] > 0]

    def save_portfolio(self, aggregated_data: List[Dict[str, Any]]) -> None:
        """
        Atomically saves the aggregated data to the target portfolio.json file.

        Args:
            aggregated_data: The list of aggregated holdings to save.
        """
        # Ensure directory exists
        dir_name = os.path.dirname(self.output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        with open(self.output_path, "w") as f:
            json.dump(aggregated_data, f, indent=2)
