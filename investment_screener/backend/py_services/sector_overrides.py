#!/usr/bin/env python3
"""
sector_overrides.py - Python utility script.

Purpose:
    Canonical sector/industry overrides for stocks Yahoo Finance mis-classifies.
Key Input Dependencies:
    - investment_screener/backend/data/portfolio.json (Saves sector classifications)

Layer:
    Backend / Python Services

Usage Examples:
    TBD

Key Functions (Index):
    None

Key Input Dependencies:
    None

Key Output Dependencies:
    None
"""
SECTOR_OVERRIDES: dict[str, dict[str, str]] = {
    "HUMN": {"sector": "Technology",     "industry": "Software - Application"},
    "KOID": {"sector": "Technology",     "industry": "Software - Application"},
    "IBIT": {"sector": "Cryptocurrency", "industry": "Bitcoin ETF"},
    "SOLZ": {"sector": "Cryptocurrency", "industry": "Crypto Assets"},
    "ETHA": {"sector": "Cryptocurrency", "industry": "Ethereum ETF"},
    "COIN": {"sector": "Cryptocurrency", "industry": "Crypto Exchange"},
    "CRCL": {"sector": "Cryptocurrency", "industry": "Crypto Infrastructure"},
    "SOL":  {"sector": "Cryptocurrency", "industry": "Crypto Network"},
    "PSU-U.TO": {"sector": "CASH", "industry": "CASH"},
    "PSU.U.TO": {"sector": "CASH", "industry": "CASH"},
    "PSU.U":    {"sector": "CASH", "industry": "CASH"},
}
