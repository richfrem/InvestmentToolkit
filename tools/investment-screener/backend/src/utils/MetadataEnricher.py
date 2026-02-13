#!/usr/bin/env python3
"""
MetadataEnricher.py
=====================================

Purpose:
    Enriches portfolio holdings with sector and industry data using yfinance.
    Implements ADR 018.

Layer: Retrieve

Usage:
    Imported by QuestradeDataEngine.py.
"""

import logging
from typing import List, Dict, Any
import yfinance as yf

# Sector/industry overrides for stocks Yahoo doesn't classify correctly (shared pattern)
SECTOR_OVERRIDES = {
    "HUMN": {"sector": "Technology", "industry": "Software - Application"},
    "KOID": {"sector": "Technology", "industry": "Software - Application"},
    "IBIT": {"sector": "Cryptocurrency", "industry": "Bitcoin ETF"},
    "SOLZ": {"sector": "Cryptocurrency", "industry": "Crypto Assets"},
    "ETHA": {"sector": "Cryptocurrency", "industry": "Ethereum ETF"},
    "COIN": {"sector": "Cryptocurrency", "industry": "Crypto Exchange"},
    "CRCL": {"sector": "Cryptocurrency", "industry": "Crypto Infrastructure"},
    "SOL":  {"sector": "Cryptocurrency", "industry": "Crypto Network"},
}

class MetadataEnricher:
    """
    Utility for enriching portfolio holdings with external metadata.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def resolve_classification(self, symbol: str, info: Dict[str, Any]) -> tuple:
        """
        Determines the sector and industry for a stock based on hierarchy of overrides.
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

    def enrich_holdings(self, holdings: List[Dict[str, Any]]) -> List[Dict[Dict, Any]]:
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
