#!/usr/bin/env python3
"""
align_all_strategies.py
=====================================

Purpose:
    Performs a clean, systematic taxonomy realignment across all investments in domain_model.sqlite.
    Registers any missing sub-strategies (power-infrastructure, titans-cloud) and assigns
    every holding and watchlist ticker to its accurate Pillar and Sub-Strategy according to the
    active Investment Thesis.

Layer:
    Backend / py_services / Persistence

Usage:
    python3 investment_screener/backend/py_services/align_all_strategies.py

Key Functions:
    - register_sub_strategies(conn: sqlite3.Connection) -> None: Inserts missing sub-strategy definitions.
    - apply_taxonomy_mapping(conn: sqlite3.Connection) -> dict: Updates all investment records to canonical pillars/strategies.
    - main() -> None: CLI entrypoint.

Key Input Dependencies:
    - investment_screener/backend/data/domain_model.sqlite (strategy_pillar, sub_strategy, investment tables)
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, Tuple, Any

_HERE = Path(__file__).resolve().parent
DB_PATH = _HERE / ".." / "data" / "domain_model.sqlite"

# Canonical sub-strategy registration definitions: sub_strategy_id -> (pillar_id, name)
NEW_SUB_STRATEGIES: Dict[str, Tuple[str, str]] = {
    "power-infrastructure": ("power", "Power & Energy Infrastructure"),
    "titans-cloud": ("titans", "AI Titans & Hyperscale Cloud"),
}

# Master Ticker Taxonomy Map: symbol -> (pillar_id, sub_strategy_id)
TAXONOMY_MAP: Dict[str, Tuple[str, str]] = {
    # 1. Data Center Infrastructure & HPC Compute
    "APLD": ("datainfra", "ai-infrastructure"),
    "CORZ": ("datainfra", "ai-infrastructure"),
    "CRWV": ("datainfra", "ai-infrastructure"),
    "IREN": ("datainfra", "ai-infrastructure"),
    "NBIS": ("datainfra", "ai-infrastructure"),
    "SHAZ": ("datainfra", "ai-infrastructure"),
    "RIOT": ("datainfra", "ai-infrastructure"),
    "BTDR": ("datainfra", "ai-infrastructure"),
    "CLSK": ("datainfra", "ai-infrastructure"),
    "WYFI": ("datainfra", "ai-infrastructure"),
    "VRT": ("datainfra", "ai-infrastructure"),
    "EQIX": ("datainfra", "ai-infrastructure"),
    "ANET": ("datainfra", "ai-infrastructure"),
    "CIFR": ("datainfra", "ai-infrastructure"),
    "HUT": ("datainfra", "ai-infrastructure"),
    "BITF": ("datainfra", "ai-infrastructure"),
    "HIVE": ("datainfra", "ai-infrastructure"),

    # 2. Power & Energy Infrastructure
    "BE": ("power", "power-infrastructure"),
    "CEG": ("power", "power-infrastructure"),
    "VST": ("power", "power-infrastructure"),
    "OKLO": ("power", "power-infrastructure"),
    "PSIX": ("power", "power-infrastructure"),
    "BW": ("power", "power-infrastructure"),
    "LBRT": ("power", "power-infrastructure"),
    "NEE": ("power", "power-infrastructure"),
    "PLUG": ("power", "power-infrastructure"),
    "EQT": ("power", "power-infrastructure"),
    "SEI": ("power", "power-infrastructure"),
    "PUMP": ("power", "power-infrastructure"),

    # 3. Frontier Compute & Silicon Accelerators
    "AMAT": ("compute", "sa-asi-race"),
    "CBRS": ("compute", "sa-asi-race"),
    "INTC": ("compute", "sa-asi-race"),
    "STM": ("compute", "sa-asi-race"),
    "TSM": ("compute", "sa-asi-race"),
    "NVDA": ("compute", "sa-asi-race"),
    "AMD": ("compute", "sa-asi-race"),
    "AVGO": ("compute", "sa-asi-race"),
    "ASML": ("compute", "sa-asi-race"),
    "QCOM": ("compute", "sa-asi-race"),
    "ARM": ("compute", "sa-asi-race"),
    "TSEM": ("compute", "sa-asi-race"),
    "ALAB": ("compute", "sa-asi-race"),
    "CDNS": ("compute", "sa-asi-race"),
    "SNPS": ("compute", "sa-asi-race"),

    # 4. Memory, High-Density Storage & Packaging
    "MU": ("compute", "memory-storage-packaging"),
    "SKHY": ("compute", "memory-storage-packaging"),
    "SNDK": ("compute", "memory-storage-packaging"),

    # 5. AI Titans & Hyperscale Cloud
    "GOOG": ("titans", "titans-cloud"),
    "META": ("titans", "titans-cloud"),
    "MSFT": ("titans", "titans-cloud"),
    "AMZN": ("titans", "titans-cloud"),
    "AAPL": ("titans", "titans-cloud"),

    # 6. AI-Native Cybersecurity
    "ZS": ("security", "cybersecurity"),
    "PANW": ("security", "cybersecurity"),
    "CRWD": ("security", "cybersecurity"),
    "NET": ("security", "cybersecurity"),

    # 7. Ontological Enterprise AI & Operating Systems
    "PLTR": ("security", "ontological-os"),

    # 8. Space Data Centers & Defense Infrastructure
    "MP": ("defense", "defense-ai-space"),
    "SPCX": ("defense", "defense-ai-space"),
    "CACI": ("defense", "defense-ai-space"),
    "KRMN": ("defense", "defense-ai-space"),
    "RDW": ("defense", "defense-ai-space"),
    "RKLB": ("defense", "defense-ai-space"),
    "LDOS": ("defense", "defense-ai-space"),

    # 9. Humanoid Robotics & Physical AI
    "HUMN": ("robotics", "robotics-automation"),
    "KOID": ("robotics", "robotics-automation"),
    "TSLA": ("robotics", "robotics-automation"),
    "SYM": ("robotics", "robotics-automation"),

    # 10. Photonics & Optical Interconnect
    "FOTO": ("photonics", "photonics-optical"),
    "COHR": ("photonics", "photonics-optical"),
    "LITE": ("photonics", "photonics-optical"),
    "CIEN": ("photonics", "photonics-optical"),
    "CRDO": ("photonics", "photonics-optical"),
    "GLW": ("photonics", "photonics-optical"),
    "APH": ("photonics", "photonics-optical"),
    "POET": ("photonics", "photonics-optical"),
    "VIAV": ("photonics", "photonics-optical"),

    # 11. Sovereign Finance & Autonomous AI Settlement
    "COIN": ("sovfin", "sovereign-finance"),
    "CRCL": ("sovfin", "sovereign-finance"),
    "IBIT": ("sovfin", "sovereign-finance"),
    "ETHA": ("sovfin", "sovereign-finance"),
    "SOLZ": ("sovfin", "sovereign-finance"),

    # 12. Quality SaaS & Oversold Leaders
    "CRM": ("quality_saas", "quality-saas"),
    "NOW": ("quality_saas", "quality-saas"),
    "TEAM": ("quality_saas", "quality-saas"),
    "DXYZ": ("quality_saas", "preipo-access"),

    # 13. Healthcare AI & Metabolic Rewriting
    "LLY": ("biohealth", "metabolic-rewriting"),
    "CRSP": ("biohealth", "metabolic-rewriting"),
    "TEM": ("biohealth", "metabolic-rewriting"),

    # 14. Quantum Computing
    "IONQ": ("quantum", "quantum-computing"),
    "QBTS": ("quantum", "quantum-computing"),
    "RGTI": ("quantum", "quantum-computing"),
    "QUBT": ("quantum", "quantum-computing"),
    "WQTM": ("quantum", "quantum-computing"),

    # 15. Strategic Reserve (Cash)
    "CASH_USD": ("cash", "cash"),
    "USD_CASH": ("cash", "cash"),
    "PSU-U.TO": ("cash", "cash"),
}


def register_sub_strategies(conn: sqlite3.Connection) -> None:
    """Inserts any missing sub-strategies into sub_strategy table."""
    for sub_id, (pillar_id, name) in NEW_SUB_STRATEGIES.items():
        conn.execute("""
            INSERT INTO sub_strategy (sub_strategy_id, pillar_id, name)
            VALUES (?, ?, ?)
            ON CONFLICT(sub_strategy_id) DO UPDATE SET
                pillar_id = excluded.pillar_id,
                name = excluded.name;
        """, (sub_id, pillar_id, name))


def apply_taxonomy_mapping(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Updates investment table with canonical pillar and sub-strategy alignments."""
    updated_count = 0
    not_found = []

    for sym, (pillar_id, sub_strategy_id) in TAXONOMY_MAP.items():
        cur = conn.execute("""
            UPDATE investment
            SET pillar_id = ?, sub_strategy_id = ?, updated_at = datetime('now')
            WHERE symbol = ?;
        """, (pillar_id, sub_strategy_id, sym))
        if cur.rowcount > 0:
            updated_count += cur.rowcount
        else:
            not_found.append(sym)

    return {
        "updated_count": updated_count,
        "not_found": not_found,
    }


def main() -> None:
    """CLI execution entrypoint."""
    if not DB_PATH.exists():
        print(f"Error: Database {DB_PATH} not found.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        register_sub_strategies(conn)
        res = apply_taxonomy_mapping(conn)
        conn.commit()
        print(f"✅ Sub-strategies registered.")
        print(f"✅ Taxonomy alignment complete. Updated {res['updated_count']} ticker records in domain_model.sqlite.")
        if res["not_found"]:
            print(f"ℹ️ Note: {len(res['not_found'])} mapped symbols not currently in DB: {res['not_found']}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during alignment: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
