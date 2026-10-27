#!/usr/bin/env python3
"""wave4_path_fixes.py - one-off: fixes the fixed-depth roots and sibling-script lookups of the files moved in wave 4
that the rewrite tool leaves to a human. Idempotent. Retired with the migration."""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ROOT_EXPR = 'next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())'
SKILLS = ROOT / "plugins/portfolio-advisor/.apm/skills"
PYS = ROOT / "investment_screener/backend/py_services"
ETESTS = ROOT / "investment_screener/backend/tests/py_services"
ledger = [r for r in csv.DictReader(open(ROOT / "docs/plans/apm-migration/master_migration_inventory.csv")) if r["wave"] == "4"]
eng_tests = [ROOT / r["new_path"] for r in ledger if r["action"] == "MOVED_TO_ENGINE_TESTS" and r["new_path"].endswith(".py")]
hub_py = [p for h in SKILLS.iterdir() for sub in ("scripts", "tests") for p in (h / sub).glob("*.py")] if SKILLS.exists() else []

def edit(path: Path, pairs, optional=True):
    s = path.read_text(); ch = False
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b); ch = True
        elif not optional:
            raise AssertionError(f"{path.name}: {a[:60]!r}")
    if ch:
        path.write_text(s)
    return ch

n = 0
for f in hub_py + eng_tests:
    n += edit(f, [("Path(__file__).resolve().parents[3]", ROOT_EXPR)])
for f in eng_tests:   # engine tests used to sit beside the plugin's scripts/ folder
    n += edit(f, [('Path(__file__).resolve().parents[1] / "scripts/dcf_scenarios.py"', f'{ROOT_EXPR} / "investment_screener/backend/py_services/dcf_scenarios.py"'),
                  ('Path(__file__).resolve().parents[1] / "scripts"', f'{ROOT_EXPR} / "investment_screener/backend/py_services"'),
                  ('_PLUGIN_ROOT: Path = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(_PLUGIN_ROOT / "scripts"))',
                   f'sys.path.insert(0, str({ROOT_EXPR} / "investment_screener/backend/py_services"))')])
H = SKILLS
edit(H / "auditing-portfolio-data/scripts/audit_coverage.py", [(
    '_DEFAULT_DB: Path = _HERE.parents[2] / "investment_screener" / "backend" / "data" / "domain_model.sqlite"\nif not _DEFAULT_DB.exists():\n    _DEFAULT_DB = _HERE.parents[1] / "investment_screener" / "backend" / "data" / "domain_model.sqlite"\n',
    '_DEFAULT_DB: Path = next((p for p in _HERE.parents if (p / "investment_screener").is_dir()), _HERE) / "investment_screener" / "backend" / "data" / "domain_model.sqlite"\n')])
edit(H / "valuing-investments/scripts/consolidate_research.py", [("repo_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))",
    'repo_root = str(next(p for p in __import__("pathlib").Path(script_dir).parents if (p / "investment_screener").is_dir()))')])
edit(H / "tracking-13f-filings/scripts/fetch_13f.py", [('DATA_DIR = SCRIPT_DIR.parent.parent.parent / "investment_screener" / "backend" / "data" / "13f"',
    'DATA_DIR = next(p for p in SCRIPT_DIR.parents if (p / "investment_screener").is_dir()) / "investment_screener" / "backend" / "data" / "13f"')])
edit(H / "running-portfolio-reviews/scripts/news_sweep.py", [('_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))',
    '_REPO_ROOT = str(next(p for p in __import__("pathlib").Path(__file__).resolve().parents if (p / "investment_screener").is_dir()))')])
# engine shim for hub scripts that import backend modules without finding py_services themselves
stems = {p.stem for p in PYS.glob("*.py")} - set(sys.stdlib_module_names)
SHIM = '''# Engine modules (recommendation, update_targets, repo_root, ...) live in the backend's py_services folder.
_ENGINE_DIR = next((p / "investment_screener/backend/py_services" for p in __import__("pathlib").Path(__file__).resolve().parents
                    if (p / "investment_screener").is_dir()), None)
if _ENGINE_DIR is not None and str(_ENGINE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_ENGINE_DIR))
'''
rx = re.compile(r"^(?:from|import)\s+(" + "|".join(sorted(map(re.escape, stems), key=len, reverse=True)) + r")\b", re.M)
for h in SKILLS.iterdir():
    for f in (h / "scripts").glob("*.py"):
        s = f.read_text()
        if "_ENGINE_DIR" in s or ("py_services" in s and "sys.path" in s):
            continue
        m = rx.search(s)
        if m:
            f.write_text(s[:m.start()] + SHIM + s[m.start():]); n += 1
print("edits:", n)
