#!/usr/bin/env python3
"""
batch_intake_watchlist.py - Batch ingest valuation models for watchlist candidates.
"""
import sys
from pathlib import Path
import yfinance as yf

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from stock_intake_persist import persist_intake_payload

candidates = [
    ('ARM', 'compute', 'sa-asi-race', 280.0, 48.0, 32.0, 65.0, 'Semiconductor IP & ISA architecture monopoly powering edge and data center AI compute'),
    ('CDNS', 'compute', 'sa-asi-race', 350.0, 22.0, 28.0, 42.0, 'EDA software & custom silicon design platform essential for AI chip engineering'),
    ('SNPS', 'compute', 'sa-asi-race', 460.0, 20.0, 26.0, 40.0, 'Electronic design automation and semiconductor IP leader'),
    ('QCOM', 'compute', 'sa-asi-race', 210.0, 16.0, 25.0, 22.0, 'On-device NPU compute and mobile/automotive AI acceleration platform'),
    ('IBM', 'compute', 'sa-asi-race', 245.0, 8.0, 14.0, 22.0, 'Enterprise AI consulting and hybrid cloud platform with quantum leadership'),
    ('DELL', 'datainfra', 'ai-infrastructure', 165.0, 15.0, 8.0, 18.0, 'Enterprise AI server integration and high-density liquid-cooled rack infrastructure'),
    ('SMCI', 'datainfra', 'ai-infrastructure', 52.0, 25.0, 6.5, 16.0, 'Modular server architecture and liquid-cooled data center racks'),
    ('HIVE', 'datainfra', 'ai-infrastructure', 6.5, 35.0, 12.0, 20.0, 'Tier-3 green energy data center infrastructure and GPU cloud hosting'),
    ('LDOS', 'defense', 'defense-ai-space', 165.0, 10.0, 8.5, 20.0, 'Mission-critical defense AI IT and national security intelligence systems'),
    ('CIEN', 'photonics', 'photonics-optical', 95.0, 18.0, 14.0, 25.0, 'High-capacity optical routing and data center interconnect solutions'),
    ('GLW', 'photonics', 'photonics-optical', 55.0, 12.0, 15.0, 24.0, 'Specialty optical fiber and high-density optical cable assemblies for AI clusters'),
    ('APH', 'photonics', 'photonics-optical', 92.0, 16.0, 18.0, 30.0, 'Precision electrical and fiber optic interconnects and sensors'),
    ('CRDO', 'photonics', 'photonics-optical', 45.0, 38.0, 22.0, 38.0, 'Active electrical cables (AEC) and optical DSPs for hyperscale clusters'),
    ('AAOI', 'photonics', 'photonics-optical', 28.0, 30.0, 10.0, 22.0, 'Optical transceivers and silicon photonics lasers for data centers'),
    ('AXTI', 'photonics', 'photonics-optical', 6.0, 25.0, 8.0, 20.0, 'Compound semiconductor substrates (InP, GaAs) for photonic devices'),
    ('VIAV', 'photonics', 'photonics-optical', 14.0, 10.0, 12.0, 18.0, 'Optical network testing, lab instrumentation, and optical security coatings'),
    ('GEV', 'power', 'power-infrastructure', 420.0, 18.0, 11.0, 32.0, 'Heavy-duty gas turbines, wind electrification, and utility-scale power grid tech'),
    ('NEE', 'power', 'power-infrastructure', 92.0, 10.0, 24.0, 24.0, 'Largest US clean energy utility providing dedicated PPA contracts for data centers'),
    ('PLUG', 'power', 'power-infrastructure', 3.5, 25.0, 5.0, 15.0, 'Turnkey hydrogen fuel cells and on-site backup power systems'),
    ('SHOP', 'quality_saas', 'quality-saas', 160.0, 24.0, 18.0, 45.0, 'Global merchant commerce operating system with embedded AI checkout agents'),
    ('QUBT', 'quantum', 'quantum-computing', 4.5, 40.0, 8.0, 25.0, 'Full-stack quantum computing and nanophotonic quantum entropy solutions'),
    ('RBLX', 'robotics', 'robotics-automation', 72.0, 22.0, 15.0, 35.0, 'Spatial 3D simulation engine and virtual world physics for synthetic robot training'),
    ('DDOG', 'security', 'cybersecurity', 155.0, 26.0, 20.0, 50.0, 'Cloud observability, synthetic monitoring, and cloud-native security platform'),
    ('FTNT', 'security', 'cybersecurity', 96.0, 16.0, 25.0, 32.0, 'Converged networking and AI-driven secure access service edge (SASE) firewalls'),
    ('NET', 'security', 'cybersecurity', 140.0, 28.0, 15.0, 60.0, 'Global edge network, Zero Trust security fabric, and Workers serverless AI platform'),
    ('HOOD', 'sovfin', 'sovereign-finance', 42.0, 28.0, 26.0, 28.0, 'Modern financial operating system and retail digital asset gateway'),
    ('SOFI', 'sovfin', 'sovereign-finance', 18.5, 22.0, 18.0, 24.0, 'Digital bank and Galileo financial technology infrastructure'),
    ('PYPL', 'sovfin', 'sovereign-finance', 88.0, 8.0, 16.0, 16.0, 'Global digital wallet, merchant settlement, and PYUSD sovereign stablecoin rails'),
    ('SOLZ', 'sovfin', 'sovereign-finance', 35.0, 30.0, 20.0, 25.0, 'Solana institutional staking and digital asset treasury exposure'),
    ('NFLX', 'titans', 'titans-cloud', 920.0, 16.0, 24.0, 35.0, 'Global entertainment network and generative AI content delivery platform')
]

def main():
    print(f"Ingesting {len(candidates)} watchlist valuation models into SQLite...")
    for sym, pid, sub, fv, growth, margin, exit_pe, summary in candidates:
        try:
            f = yf.Ticker(sym).fast_info
            price = float(f.last_price or fv)
        except Exception:
            price = fv
            
        payload = {
            "symbol": sym,
            "pillarId": pid,
            "subStrategyId": sub,
            "targetWeight": 0.0,
            "lifecycleStatus": "candidate",
            "isWatchlisted": True,
            "agentRationale": summary,
            "dcf": {
                "fairValue": fv,
                "action": "WATCHLIST",
                "model": "DCF_5Y_SCENARIO",
                "rationale": summary,
                "source": "AI_AGENT",
                "snapshot": {
                    "currentPrice": price,
                    "targetPrice": fv,
                    "growthRate": growth,
                    "netMargin": margin
                },
                "scenarios": {
                    "bear": {"growthRate": growth * 0.6, "netMargin": margin * 0.7, "exitPe": exit_pe * 0.7, "weight": 0.25, "scenarioPrice": fv * 0.6},
                    "base": {"growthRate": growth, "netMargin": margin, "exitPe": exit_pe, "weight": 0.50, "scenarioPrice": fv},
                    "bull": {"growthRate": growth * 1.3, "netMargin": margin * 1.2, "exitPe": exit_pe * 1.3, "weight": 0.25, "scenarioPrice": fv * 1.4}
                }
            }
        }
        persist_intake_payload(payload)
        print(f"  ✓ {sym:<6} -> FV: ${fv:.2f} | Pillar: {pid:<10} | Sub: {sub}")

    print("Valuation intake complete!")

if __name__ == "__main__":
    main()
