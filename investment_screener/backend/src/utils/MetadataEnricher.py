#!/usr/bin/env python3
"""
MetadataEnricher.py - Portfolio holdings metadata enrichment utility.

Purpose:
    Enriches portfolio holdings with sector and industry metadata using yfinance.
    Handles classification logic and applies overrides for assets with inconsistent reporting.

Layer:
    Backend / Utils / Data Enrichment

Usage Examples:
    enricher = MetadataEnricher()
    enriched_data = enricher.enrich_holdings(raw_holdings)

Key Functions:
    - enrich_holdings() - Primary entry point to fetch and apply missing metadata to a list of holdings
    - resolve_classification() - Implements the hierarchy of classification logic (Overrides -> Yahoo Finance -> Fallbacks)

Key Input Dependencies:
    - py_services/sector_overrides.py (SECTOR_OVERRIDES)

Key Output Dependencies:
    None
"""

import sys
import os
import logging
from typing import List, Dict, Any, Tuple
import yfinance as yf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../py_services'))
from sector_overrides import SECTOR_OVERRIDES

class MetadataEnricher:
    """Utility for enriching portfolio holdings with external metadata."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def resolve_classification(self, symbol: str, info: Dict[str, Any]) -> Tuple[str, str]:
        """Determines the sector and industry for a stock based on hierarchy of overrides.

        Args:
            symbol: Ticker symbol string.
            info: Dictionary containing Ticker info metadata from yfinance.

        Returns:
            A tuple containing (sector, industry) strings.
        """
        symbol_upper = symbol.upper()
        
        # Priority 1: System-level hardcoded overrides
        if symbol_upper in SECTOR_OVERRIDES:
            sys_override = SECTOR_OVERRIDES[symbol_upper]
            return sys_override.get("sector", "Other"), sys_override.get("industry", "Other")

        # Priority 2: Yahoo Finance data
        sector = info.get("sector")
        industry = info.get("industry")
        
        if not sector or sector == "Unknown":
            # Attempt to map from quoteType for ETFs/Crypto
            quote_type = info.get("quoteType")
            if quote_type == "ETF":
                return "Financial Services", "Exchange Traded Fund"
            elif quote_type == "CRYPTOCURRENCY":
                return "Cryptocurrency", "Digital Asset"

        return sector or "Other", industry or "Other"

    def enrich_holdings(self, holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetches missing metadata for a list of holdings.
        
        Args:
            holdings: List of holding dictionaries (mutated in place).
            
        Returns:
            The enriched list of holdings.
        """
        self.logger.info(f"Enriching {len(holdings)} holdings with metadata...")
        
        for holding in holdings:
            symbol = holding["symbol"]
            
            # Skip if we already have valid metadata (unless it's 'Other')
            if holding.get("sector") and holding["sector"] != "Other" and \
               holding.get("industry") and holding["industry"] != "Other":
                continue

            try:
                self.logger.info(f"Fetching metadata for {symbol}...")
                stock = yf.Ticker(symbol)
                info = stock.info
                
                sector, industry = self.resolve_classification(symbol, info)
                
                holding["sector"] = sector
                holding["industry"] = industry
                
                # Also update name if missing
                if not holding.get("name") or holding["name"] == symbol:
                    holding["name"] = info.get("shortName", symbol)
                    
            except Exception as e:
                self.logger.warning(f"Failed to enrich {symbol}: {e}")
                # Fallback to Other if not already set
                holding.setdefault("sector", "Other")
                holding.setdefault("industry", "Other")

        return holdings
