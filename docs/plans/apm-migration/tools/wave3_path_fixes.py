#!/usr/bin/env python3
"""wave3_path_fixes.py - one-off: fixes the path constructs of the moved tradingview scripts and tests
that the rewrite tool deliberately leaves to a human (fixed-depth parents[N], directory-level sys.path
inserts, the shared _find_scripts_dir helper). Idempotent. Retired with the migration."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ROOT_EXPR = 'next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())'
A = ROOT / "plugins/tradingview/.apm/skills/operating-tradingview-charts"
B = ROOT / "plugins/tradingview/.apm/skills/trading-via-tradingview"
C = ROOT / "plugins/tradingview/.apm/skills/analyzing-charts"
ENGINE_T = ROOT / "investment_screener/backend/tests/py_services"
PYS = ROOT / "investment_screener/backend/py_services"
HUB_SCRIPTS = 'Path(__file__).resolve().parents[1] / "scripts"'

SHIM = '''# Engine modules (tv_client, tv_launch, place_order, ...) live in the backend's py_services folder.
_ENGINE_DIR = next((p / "investment_screener/backend/py_services" for p in __import__("pathlib").Path(__file__).resolve().parents
                    if (p / "investment_screener").is_dir()), None)
if _ENGINE_DIR is not None and str(_ENGINE_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_ENGINE_DIR))
'''
ENGINE_IMPORT = re.compile(r"^(from|import) (tv_client|tv_launch|tv_health_check|place_order|fetch_broker_data|tv_account_coverage)\b", re.M)
HELPER_OLD = '''        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
    raise ImportError("tv_client.py not found — check plugin installation or set TV_CDP_DIR.")'''
HELPER_NEW = '''        if (candidate / "scripts" / "tv_client.py").exists():
            return candidate / "scripts"
        engine = candidate / "investment_screener" / "backend" / "py_services"
        if (engine / "tv_client.py").exists():
            return engine
    raise ImportError("tv_client.py not found — expected in investment_screener/backend/py_services (set TV_CDP_DIR for the Node engine).")'''

def edit(path: Path, pairs, optional=False):
    s = path.read_text()
    changed = False
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b); changed = True
        elif not optional and b not in s:
            raise AssertionError(f"{path.name}: pattern not found: {a[:70]!r}")
    if changed:
        path.write_text(s)
    return changed

n = 0
# 1. fixed-depth repo roots (hub scripts and every moved test)
for f in list(A.glob("scripts/*.py")) + list(A.glob("tests/*.py")) + list(B.glob("scripts/*.py")) + list(B.glob("tests/*.py")) \
        + list(C.glob("scripts/*.py")) + list(C.glob("tests/*.py")) + [ENGINE_T / x for x in
        ("test_account_parsing.py", "test_fetch_broker_data_compare.py", "test_fetch_broker_data_exchange_rate.py",
         "test_tv_account_coverage.py", "tv_test_harness.py")]:
    n += edit(f, [("Path(__file__).resolve().parents[3]", ROOT_EXPR)], optional=True)
# 2. the shared helper: also look in the backend's py_services folder
for f in list(A.glob("scripts/*.py")) + list(B.glob("scripts/*.py")) + list(C.glob("scripts/*.py")):
    n += edit(f, [(HELPER_OLD, HELPER_NEW)], optional=True)
# 3. hub scripts that imported tv_client from their own folder: add the engine path before the import
for f in list(A.glob("scripts/*.py")) + list(B.glob("scripts/*.py")) + list(C.glob("scripts/*.py")):
    s = f.read_text()
    if "_find_scripts_dir(" in s or "_ENGINE_DIR" in s:
        continue
    m = ENGINE_IMPORT.search(s)
    if m:
        f.write_text(s[:m.start()] + SHIM + s[m.start():]); n += 1
# 4. specific constructs
edit(A / "scripts/tv_thesis_overlay.py", [('PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, "../../../"))',
     'PROJECT_ROOT = str(next(p for p in Path(SCRIPTS_DIR).parents if (p / "investment_screener").is_dir()))')])
s = (A / "scripts/tv_thesis_overlay.py").read_text()
if "from pathlib import Path" not in s:
    (A / "scripts/tv_thesis_overlay.py").write_text(s.replace("import json\n", "import json\nfrom pathlib import Path\n", 1))
edit(A / "scripts/tv_pine_manager.py", [("_REPO_ROOT = _SCRIPT_DIR.parent.parent.parent",
     '_REPO_ROOT = next(p for p in _SCRIPT_DIR.parents if (p / "investment_screener").is_dir())')])
edit(B / "scripts/tv_trades_import.py", [("_REPO_ROOT = _HERE.parents[2]",
     '_REPO_ROOT = next(p for p in _HERE.parents if (p / "investment_screener").is_dir())')])
edit(B / "scripts/watchlist_manager.py", [('sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))\n', '')], optional=True)
edit(B / "scripts/tv_price_refresh.py", [('script = Path(__file__).resolve().parent / "fetch_broker_data.py"',
     'script = PY_SERVICES / "fetch_broker_data.py"')], optional=True)
edit(PYS / "tv_health_check.py", [('PINE_DIR = REPO_ROOT / "plugins" / "tradingview" / "assets" / "pinescript-indicators"',
     'PINE_DIR = REPO_ROOT / "plugins" / "tradingview" / ".apm" / "skills" / "operating-tradingview-charts" / "assets" / "pinescript-indicators"')])
# 5. tests: directory-level sys.path inserts and script dirs
for f in list(A.glob("tests/*.py")):
    edit(f, [('sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))', f"sys.path.insert(0, str({HUB_SCRIPTS}))")], optional=True)
for f in list(B.glob("tests/*.py")):
    edit(f, [('sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))', f"sys.path.insert(0, str({HUB_SCRIPTS}))"),
             ('SCRIPTS_DIR = REPO_ROOT / "plugins/tradingview/scripts"', f"SCRIPTS_DIR = {HUB_SCRIPTS}")], optional=True)
for f in list(C.glob("tests/*.py")):
    edit(f, [('sys.path.insert(0, str(repo_root / "plugins/tradingview/scripts"))', f"sys.path.insert(0, str({HUB_SCRIPTS}))")], optional=True)
for f in ("test_tv_account_coverage.py",):
    edit(ENGINE_T / f, [('sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/scripts"))',
         'sys.path.insert(0, str(REPO_ROOT / "plugins/tradingview/.apm/skills/trading-via-tradingview/scripts"))')], optional=True)
edit(ENGINE_T / "tv_test_harness.py", [('sys.path.insert(0, str(REPO_ROOT / "plugins" / "tradingview" / "scripts"))',
     'sys.path.insert(0, str(REPO_ROOT / "investment_screener" / "backend" / "py_services"))')], optional=True)
print("edits applied")
