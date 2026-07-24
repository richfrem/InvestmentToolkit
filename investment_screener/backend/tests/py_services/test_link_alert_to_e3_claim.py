"""
Task 5C-5: E3 Claim Linking

Tests for alert_manager._latest_alert_metadata() / link_alert_to_claim() —
composes 5C-4's AlertMetadata/save_alert_metadata()/load_alert_metadata()
with claim lookups to link an existing alert's metadata to a claim, for
audit ("was this alert based on this claim?").

alerts_state.jsonl is append-only (5C-4's own design) — "linking" appends a
NEW snapshot record for the same alert `id` with `linked_claim_id` set,
never rewrites in place. `_latest_alert_metadata()` resolves "current state
of alert X" by taking the LAST matching record (file order is oldest-first).

IMPORTANT: All tests monkeypatch the module-level ALERTS_STATE_PATH constant
to a pytest tmp_path location. None of these tests may write to the real
investment_screener/backend/data/alerts_state.jsonl path. Wave 5D Task 8
cut `link_alert_to_claim()` over from `prediction_ledger.load_predictions()`
(a JSONL read against the now-archived `predictions.jsonl`) to
`_load_predictions_from_ledger()` (a real `intelligence_event` read) — this
consumer was missed by the original Task 3 cutover and only found via
Task 8's archive-prerequisite grep. Test 0 below exercises the real
`intelligence_event` read path end-to-end (real sqlite, tmp_path-scoped);
Tests 1-6 monkeypatch `_load_predictions_from_ledger` directly on the
`alert_manager` module (its imported reference) to a stub returning a
fixture claims list — no test reads or writes the real, tracked
data/intelligence.sqlite or the archived data/predictions.jsonl.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = REPO_ROOT / "investment_screener/backend/py_services"
sys.path.insert(0, str(SCRIPT_DIR))

import alert_manager  # noqa: E402
from alert_manager import (  # noqa: E402
    AlertMetadata,
    _latest_alert_metadata,
    link_alert_to_claim,
    load_alert_metadata,
    save_alert_metadata,
)


@pytest.fixture
def alerts_state_path(tmp_path, monkeypatch):
    """Point ALERTS_STATE_PATH at a temp file for the duration of a test."""
    path = tmp_path / "alerts_state.jsonl"
    monkeypatch.setattr(alert_manager, "ALERTS_STATE_PATH", path)
    return path


def _make_record(**overrides) -> AlertMetadata:
    fields = {
        "id": "alert-123",
        "ticker": "NVDA",
        "price": 150.0,
        "direction": "above",
        "type": "price",
        "linked_claim_id": None,
        "created_at": "2026-07-13T12:00:00+00:00",
        "fired_at": None,
        "state": "pending",
    }
    fields.update(overrides)
    return AlertMetadata(**fields)


def _make_claim(**overrides) -> dict:
    fields = {
        "id": "AAPL:earnings_expectation:2026-07-12",
        "ticker": "AAPL",
        "type": "earnings_expectation",
        "claim": {},
    }
    fields.update(overrides)
    return fields


# --- Test 0: Real intelligence_event read path (Wave 5D Task 8 cutover) ---

def test_link_alert_to_claim_reads_real_claims_from_intelligence_ledger(
    alerts_state_path, tmp_path
):
    """link_alert_to_claim() must read PREDICTION_CLAIM events from
    intelligence_event (Wave 5D Task 3's cutover pattern), not
    prediction_ledger.load_predictions()'s JSONL read -- this consumer was
    missed by the original Task 3 cutover (found during Task 8's archive
    prerequisite grep) and predictions.jsonl no longer exists once archived.
    """
    from intelligence.db_client import initialize_db
    from intelligence.event_store import append_event
    from intelligence.replay_ledger import replay_events_to_db

    save_alert_metadata(_make_record(id="alert-123"))

    ledger_path = tmp_path / "observations.jsonl"
    db_path = tmp_path / "intelligence.sqlite"
    conn = initialize_db(str(db_path))
    append_event(
        str(ledger_path), event_type="PREDICTION_CLAIM", effective_at="2026-07-12",
        status="ACTIVE", title="Prediction claim: AAPL earnings_expectation (2026-07-12)",
        body_markdown="Direction: bullish, horizon: 90 days.", ticker="AAPL",
        payload={"id": "claim-abc", "ticker": "AAPL", "type": "earnings_expectation"},
        idempotency_key="prediction-claim-claim-abc",
    )
    replay_events_to_db(str(ledger_path), conn)
    conn.close()

    result = link_alert_to_claim("alert-123", "claim-abc", db_path=str(db_path))

    assert result is True
    latest = _latest_alert_metadata("alert-123")
    assert latest.linked_claim_id == "claim-abc"


# --- Test 1: Returns True and persists the link ---

def test_link_alert_to_claim_returns_true_and_persists_link(alerts_state_path, monkeypatch):
    """A matching alert + a matching claim in the mocked ledger link successfully."""
    save_alert_metadata(_make_record(id="alert-123"))
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="claim-abc")]
    )

    result = link_alert_to_claim("alert-123", "claim-abc")

    assert result is True
    latest = _latest_alert_metadata("alert-123")
    assert latest is not None
    assert latest.linked_claim_id == "claim-abc"


# --- Test 2: Returns False when alert not found ---

def test_link_alert_to_claim_returns_false_when_alert_not_found(alerts_state_path, monkeypatch):
    """No AlertMetadata record exists for alert_id; claim exists but link is a no-op."""
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="claim-abc")]
    )

    result = link_alert_to_claim("nonexistent-alert", "claim-abc")

    assert result is False
    assert load_alert_metadata() == []


# --- Test 3: Returns False when claim not found ---

def test_link_alert_to_claim_returns_false_when_claim_not_found(alerts_state_path, monkeypatch):
    """Alert metadata exists, but the claims list doesn't contain claim_id_from_e3."""
    save_alert_metadata(_make_record(id="alert-123"))
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="some-other-claim")]
    )

    result = link_alert_to_claim("alert-123", "claim-abc")

    assert result is False
    records = load_alert_metadata()
    assert len(records) == 1
    assert records[0].linked_claim_id is None


# --- Test 4: Preserves other fields ---

def test_link_alert_to_claim_preserves_other_fields(alerts_state_path, monkeypatch):
    """Only linked_claim_id and created_at differ in the newly appended record."""
    save_alert_metadata(
        _make_record(
            id="alert-123",
            ticker="NVDA",
            price=150.0,
            direction="above",
            type="price",
            fired_at=None,
            state="pending",
        )
    )
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="claim-abc")]
    )

    link_alert_to_claim("alert-123", "claim-abc")

    latest = _latest_alert_metadata("alert-123")
    assert latest.ticker == "NVDA"
    assert latest.price == 150.0
    assert latest.direction == "above"
    assert latest.type == "price"
    assert latest.state == "pending"
    assert latest.fired_at is None
    assert latest.linked_claim_id == "claim-abc"


# --- Test 5: Uses latest snapshot when multiple exist ---

def test_link_alert_to_claim_uses_latest_snapshot_when_multiple_exist(
    alerts_state_path, monkeypatch
):
    """A second (later) prior snapshot's fields win over the first when linking."""
    save_alert_metadata(
        _make_record(id="alert-123", state="pending", fired_at=None, price=150.0)
    )
    save_alert_metadata(
        _make_record(
            id="alert-123",
            state="fired",
            fired_at="2026-07-13T15:00:00+00:00",
            price=150.0,
        )
    )
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="claim-abc")]
    )

    result = link_alert_to_claim("alert-123", "claim-abc")

    assert result is True
    records = [r for r in load_alert_metadata() if r.id == "alert-123"]
    assert len(records) == 3
    newest = records[-1]
    assert newest.state == "fired"
    assert newest.fired_at == "2026-07-13T15:00:00+00:00"
    assert newest.linked_claim_id == "claim-abc"


# --- Test 6: Raises OSError on write failure ---

def test_link_alert_to_claim_raises_oserror_on_write_failure(alerts_state_path, monkeypatch):
    """save_alert_metadata()'s OSError propagates uncaught out of link_alert_to_claim()."""
    save_alert_metadata(_make_record(id="alert-123"))
    monkeypatch.setattr(
        alert_manager, "_load_predictions_from_ledger", lambda db_path: [_make_claim(id="claim-abc")]
    )

    def _failing_save(record):
        raise OSError("disk full")

    monkeypatch.setattr(alert_manager, "save_alert_metadata", _failing_save)

    with pytest.raises(OSError):
        link_alert_to_claim("alert-123", "claim-abc")
