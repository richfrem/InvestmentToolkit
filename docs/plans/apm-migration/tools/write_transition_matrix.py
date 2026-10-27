#!/usr/bin/env python3
"""write_transition_matrix.py - writes waves/wave-N/transition-matrix.md from name-map.csv (skills only).

Usage: python3 docs/plans/apm-migration/tools/write_transition_matrix.py <wave> [--note old-skill="text" ...]
"""
import csv, sys
from pathlib import Path
OUT = Path(__file__).resolve().parents[1]
wave = sys.argv[1]
notes = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
rows = [r for r in csv.DictReader(open(OUT / "name-map.csv")) if r["kind"] == "skill" and r["wave"] == wave]
md = [f"# Wave {wave}: transition matrix\n",
      "Old skill names are retired; slash commands are unchanged. Each old skill is now a mode file under `references/modes/` of its hub.\n",
      "| Legacy skill | Hub skill | Mode | Slash command | What changed |", "|:---|:---|:---|:---|:---|"]
for r in rows:
    md.append(f"| `{r['old_id']}` | `{r['hub']}` | `{r['mode']}` | `{r['command'] or '-'}` | {notes.get(r['old_id'], 'Content carried over; paths made relative to the hub.')} |")
(OUT / f"waves/wave-{wave}").mkdir(parents=True, exist_ok=True)
(OUT / f"waves/wave-{wave}/transition-matrix.md").write_text("\n".join(md) + "\n")
print(f"{len(rows)} rows")
