"""
test_run_daily.py — readiness and brief steps of the /daily runner.

Real I/O, no mocks (TDW critical-path rule): a real local HTTP server for the
health probe and real subprocesses for the brief script.

Regressions covered (2026-09-29):
  - Step 0 probed /api/health; the backend serves /health and gates /api/* with
    auth, so a running server was recorded as offline.
  - Step 1 reported COMPLETED with an invented NEUTRAL regime when the brief
    script failed, so a failed brief was indistinguishable from a real one.
  - Step 1 located daily_brief.py via the repo root instead of its own folder,
    so an installed (self-contained) skill copy reached back into the repo.
"""
import http.server
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_daily  # noqa: E402
from run_daily import server_is_running, step_1_brief  # noqa: E402


def _serve(status: int):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.end_headers()

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_any_http_response_means_the_server_is_running():
    for status in (200, 401, 404):
        srv = _serve(status)
        try:
            assert server_is_running(f"http://127.0.0.1:{srv.server_port}/health") is True
        finally:
            srv.shutdown()


def test_connection_refused_means_offline():
    assert server_is_running(f"http://127.0.0.1:{_free_port()}/health") is False


def test_readiness_probes_the_backend_health_endpoint():
    assert run_daily.HEALTH_URL == "http://localhost:3001/health"


def test_failed_brief_is_reported_as_failed(tmp_path):
    script = tmp_path / "daily_brief.py"
    script.write_text("import sys; print('boom', file=sys.stderr); sys.exit(3)\n")
    result = step_1_brief("RUN", script_path=script)
    assert result["status"] == "FAILED"
    assert "boom" in result["error"]
    assert "macro_regime" not in result


def test_successful_brief_reports_its_real_values(tmp_path):
    script = tmp_path / "daily_brief.py"
    script.write_text(
        "import json; print(json.dumps({'macro_regime': {'regime': 'RISK-ON'}, "
        "'conviction_scores': [{'ticker': 'A'}, {'ticker': 'B'}]}))\n")
    assert step_1_brief("RUN", script_path=script) == {
        "status": "COMPLETED", "macro_regime": "RISK-ON", "conviction_count": 2}


def test_brief_script_is_found_next_to_the_runner():
    assert run_daily.BRIEF_SCRIPT == Path(run_daily.__file__).parent / "daily_brief.py"


def test_scan_run_with_a_failed_brief_ends_failed(tmp_path, monkeypatch, capsys):
    import sqlite3
    db = tmp_path / "control_plane.db"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE verification_receipts (
        receipt_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, gate_name TEXT NOT NULL,
        command_executed TEXT NOT NULL, exit_code INTEGER NOT NULL, receipt_token TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    con.commit(); con.close()
    failing = tmp_path / "daily_brief.py"
    failing.write_text("import sys; sys.exit(2)\n")
    monkeypatch.setattr(run_daily, "CONTROL_PLANE_DB", db)
    monkeypatch.setattr(run_daily, "TEMP_DIR", tmp_path)
    monkeypatch.setattr(run_daily, "BRIEF_SCRIPT", failing)
    monkeypatch.setattr(sys, "argv", ["run_daily.py", "--scan"])
    assert run_daily.main() == 1
    out = capsys.readouterr()
    assert "Daily Scan Finalized" not in out.out
    terminal = sqlite3.connect(db).execute(
        "SELECT receipt_token FROM verification_receipts WHERE gate_name LIKE 'DAILY_RUN_%_TERMINAL'").fetchone()[0]
    assert '"terminal_state":"FAILED"' in terminal
