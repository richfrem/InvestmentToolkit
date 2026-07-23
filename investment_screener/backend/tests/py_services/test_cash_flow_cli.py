import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

from domain_model.db_client import initialize_db  # noqa: E402
from domain_model.cash_flow_repository import list_cash_flows  # noqa: E402
import cash_flow_cli  # noqa: E402


def test_add_writes_a_cash_flow_row(tmp_path, capsys):
    db_path = tmp_path / "test.sqlite"
    argv = [
        "--add",
        "--date", "2026-07-22",
        "--type", "deposit",
        "--amount-cad", "2000",
        "--account", "TFSA",
        "--portfolio-value-before-flow-cad", "39120",
        "--db-path", str(db_path),
    ]
    rc = cash_flow_cli.main(argv)
    assert rc == 0

    conn = initialize_db(str(db_path))
    rows = list_cash_flows(conn, account="TFSA")
    assert len(rows) == 1
    row = rows[0]
    assert row["flow_date"] == "2026-07-22"
    assert row["flow_type"] == "deposit"
    assert row["amount_cad"] == 2000.0
    assert row["portfolio_value_before_flow_cad"] == 39120.0
    assert row["account"] == "TFSA"
    assert len(row["flow_id"]) == 12

    captured = capsys.readouterr()
    assert "Added cash flow" in captured.out


def test_add_missing_required_arg_raises(tmp_path):
    db_path = tmp_path / "test.sqlite"
    argv = [
        "--add",
        "--date", "2026-07-22",
        "--type", "deposit",
        # missing --amount-cad
        "--account", "TFSA",
        "--portfolio-value-before-flow-cad", "39120",
        "--db-path", str(db_path),
    ]
    try:
        cash_flow_cli.main(argv)
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert "amount-cad" in str(exc)


def test_list_prints_all_and_filtered_rows(tmp_path, capsys):
    db_path = tmp_path / "test.sqlite"
    cash_flow_cli.main([
        "--add", "--date", "2026-01-01", "--type", "deposit",
        "--amount-cad", "1000", "--account", "TFSA",
        "--portfolio-value-before-flow-cad", "10000",
        "--db-path", str(db_path),
    ])
    cash_flow_cli.main([
        "--add", "--date", "2026-02-01", "--type", "withdrawal",
        "--amount-cad", "500", "--account", "RRSP",
        "--portfolio-value-before-flow-cad", "11000",
        "--db-path", str(db_path),
    ])

    rc = cash_flow_cli.main(["--list", "--db-path", str(db_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "TFSA" in captured.out
    assert "RRSP" in captured.out

    rc = cash_flow_cli.main(["--list", "--account", "TFSA", "--db-path", str(db_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "TFSA" in captured.out
    assert "RRSP" not in captured.out


def test_list_empty_prints_message(tmp_path, capsys):
    db_path = tmp_path / "test.sqlite"
    rc = cash_flow_cli.main(["--list", "--db-path", str(db_path)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "No cash flows found." in captured.out
