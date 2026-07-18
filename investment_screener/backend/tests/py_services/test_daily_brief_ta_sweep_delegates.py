"""Guards against daily_brief.py re-implementing ta_sweep_batch.py's save_sweep_results()
write. TA_SWEEP_PATH must only ever be written by ta_sweep_batch.py's own save logic —
daily_brief.py may read it back in, but must not open it in write mode itself.
"""
import ast
from pathlib import Path


def test_daily_brief_does_not_write_ta_sweep_path_directly():
    source = Path("plugins/portfolio-advisor/scripts/daily_brief.py").read_text()
    tree = ast.parse(source)
    # daily_brief.py must never open TA_SWEEP_PATH itself in write mode — only
    # ta_sweep_batch.py's save_sweep_results() is allowed to write that file.
    # (Other json.dump calls, e.g. for the daily brief's own snapshot file, are unrelated
    # and must remain untouched — this check is scoped to TA_SWEEP_PATH specifically.)
    write_opens_on_ta_sweep_path = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "TA_SWEEP_PATH"
        and len(node.args) > 1
        and isinstance(node.args[1], ast.Constant)
        and "w" in str(node.args[1].value)
    ]
    assert len(write_opens_on_ta_sweep_path) == 0, "daily_brief.py must not open TA_SWEEP_PATH for writing — only ta_sweep_batch.py's save_sweep_results() should write it"
