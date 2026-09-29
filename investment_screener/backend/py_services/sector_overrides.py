#!/usr/bin/env python3
"""
sector_overrides.py - curated sector/industry corrections.

Purpose:
    The single place to correct a holding's sector/industry when Yahoo Finance's
    label is missing, stale or wrong. fetch_portfolio_heatmap.resolve_sector()
    applies these before any stored or Yahoo value, and the portfolio refresh
    persists the result into domain_model.sqlite investment.sector/industry, so
    the heatmap, Portfolio Summary and tables all read the same classification.

Principle:
    Classify by the company's CURRENT principal business, in Yahoo/Morningstar
    sector names. Override only with a stated reason and source.

Layer:
    Backend / Python Services

Key Functions (Index):
    None (data module)

Key Input Dependencies:
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

    # --- Reviewed 2026-09-28 against current business mix (sources in map-debt DEBT-20260928-19) ---
    # Yahoo returned no sector; persisted as "Unknown". Semiconductor capital equipment.
    "AMAT": {"sector": "Technology", "industry": "Semiconductor Equipment & Materials"},
    # ETF: Tuttle Capital Pure Play Photonics (Lumentum, Coherent, nLIGHT, Viavi).
    "FOTO": {"sector": "Technology", "industry": "ETF - Photonics"},
    # ETFs: humanoid robotics baskets, not application software.
    "HUMN": {"sector": "Technology", "industry": "ETF - Robotics & Automation"},
    "KOID": {"sector": "Technology", "industry": "ETF - Robotics & Automation"},
    # Yahoo's "Internet Content & Information" is the Yandex legacy; now AI cloud infrastructure.
    "NBIS": {"sector": "Technology", "industry": "Information Technology Services"},
    # AI Cloud revenue passed Bitcoin mining in the June-2026 quarter; sites converting to AI.
    "IREN": {"sector": "Technology", "industry": "Information Technology Services"},
    # SpaceX: Starlink connectivity is the principal business (launch secondary).
    "SPCX": {"sector": "Communication Services", "industry": "Telecom Services"},
}
