"""Canonical sector/industry overrides for stocks Yahoo Finance mis-classifies."""

SECTOR_OVERRIDES: dict[str, dict[str, str]] = {
    "HUMN": {"sector": "Technology",     "industry": "Software - Application"},
    "KOID": {"sector": "Technology",     "industry": "Software - Application"},
    "IBIT": {"sector": "Cryptocurrency", "industry": "Bitcoin ETF"},
    "SOLZ": {"sector": "Cryptocurrency", "industry": "Crypto Assets"},
    "ETHA": {"sector": "Cryptocurrency", "industry": "Ethereum ETF"},
    "COIN": {"sector": "Cryptocurrency", "industry": "Crypto Exchange"},
    "CRCL": {"sector": "Cryptocurrency", "industry": "Crypto Infrastructure"},
    "SOL":  {"sector": "Cryptocurrency", "industry": "Crypto Network"},
}
