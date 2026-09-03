import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = REPO_ROOT / "plugins/stock-valuation/scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_projection import check_accumulate_gate, validate_projection  # noqa: E402


def _projection(action, dcf_upside=None, comps_status="ok", comps_low=None, comps_high=None,
                 implied_growth_vs_base=None, current_price=100.0, dcf_fair_value=None):
    analytics = {}
    if dcf_upside is not None:
        analytics["dcf"] = {"upsidePct": dcf_upside}
        if dcf_fair_value is not None:
            analytics["dcf"]["weightedFairValue"] = dcf_fair_value
    if comps_status == "ok":
        analytics["comps"] = {
            "status": "ok",
            "impliedPriceRange": {"low": comps_low, "high": comps_high},
        }
    else:
        analytics["comps"] = {"status": "insufficient_peer_data"}
    if implied_growth_vs_base is not None:
        analytics["reverseDcf"] = {"impliedGrowthVsBaseCase": implied_growth_vs_base}

    return {
        "aiThesis": {"action": action},
        "snapshot": {"price": current_price},
        "analyticsLog": analytics,
        "rationale": "placeholder rationale",
    }


def test_gate_passes_when_all_three_lenses_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=110.0, comps_high=130.0,
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True
    assert result["lensesAgreeing"] == 3
    assert result["lensResults"] == {"dcf": True, "comps": True, "impliedGrowth": True}


def test_gate_passes_when_exactly_two_of_three_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=110.0, comps_high=130.0,
        implied_growth_vs_base=5.0,  # disagrees (market pricing in MORE than base case)
        current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True
    assert result["lensesAgreeing"] == 2


def test_gate_blocks_when_only_one_of_three_agrees():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=70.0, comps_high=90.0,  # comps disagrees
        implied_growth_vs_base=5.0,  # impliedGrowth disagrees
        current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is False
    assert result["lensesAgreeing"] == 1


def test_gate_treats_non_converged_reverse_dcf_as_impliedgrowth_lens_disagreeing():
    """Regression: reverse_dcf.py now nulls impliedGrowthVsBaseCase when its bisection
    doesn't converge (previously it returned a numeric value even when unconverged, which
    could silently satisfy this lens). This gate must correctly treat that null the same
    as "no reverseDcf data at all" — never agreeing, never crashing on the missing key."""
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_low=110.0, comps_high=130.0,
        implied_growth_vs_base=None,  # simulates a non-converged reverse_dcf result
        current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["lensResults"]["impliedGrowth"] is False
    assert result["lensesAgreeing"] == 2  # dcf + comps only
    assert result["gatePassed"] is True  # 2 of 3 still passes the gate


def test_gate_blocks_when_zero_lenses_agree():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is False
    assert result["lensesAgreeing"] == 0


def test_gate_is_trivially_passed_for_non_accumulate_actions():
    proj = _projection(
        action="HOLD", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["gatePassed"] is True


def test_gate_treats_insufficient_comps_data_as_comps_lens_disagreeing():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, comps_status="insufficient_peer_data",
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    # Only dcf + impliedGrowth can agree = 2 of 3 -> still passes
    assert result["lensResults"]["comps"] is False
    assert result["gatePassed"] is True


def test_disagreement_note_required_above_25_percent_spread():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, dcf_fair_value=150.0,
        comps_low=100.0, comps_high=100.0,  # comps midpoint 100, dcf fair value 150 -> 50% spread
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["spreadPct"] > 25.0
    assert result["disagreementNoteRequired"] is True


def test_disagreement_note_not_required_within_25_percent_spread():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=20.0, dcf_fair_value=110.0,
        comps_low=105.0, comps_high=115.0,  # comps midpoint 110, dcf fair value 110 -> 0% spread
        implied_growth_vs_base=-3.0, current_price=100.0,
    )
    result = check_accumulate_gate(proj)
    assert result["disagreementNoteRequired"] is False


def test_validate_projection_appends_gate_failure_to_errors():
    proj = _projection(
        action="ACCUMULATE", dcf_upside=5.0, comps_low=70.0, comps_high=90.0,
        implied_growth_vs_base=5.0, current_price=100.0,
    )
    # Fill in the other required top-level fields validate_projection() checks
    proj.update({
        "ticker": "TEST", "id": "11111111-1111-1111-1111-111111111111", "source": "AI_AGENT",
        "schemaVersion": "1.2", "version": 1, "savedAt": "2026-07-04T00:00:00Z",
        "globalSettings": {"discountRate": 10, "timeHorizon": 5},
        "scenarios": {
            "bear": {"weight": 0.2, "growthRate": 5, "netMargin": 10, "exitPE": 15,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 50},
            "base": {"weight": 0.5, "growthRate": 15, "netMargin": 20, "exitPE": 25,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 100},
            "bull": {"weight": 0.3, "growthRate": 25, "netMargin": 30, "exitPE": 35,
                     "qualityMultiplier": 1.0, "shareChange": 0, "scenarioPrice": 150},
        },
    })
    errors = validate_projection(proj)
    assert any("ACCUMULATE requires" in e for e in errors)


class TestScenarioPriceFloorTie:
    """Caught live 2026-08-29 valuing BTDR: dcf_scenarios.py's own validate_scenarios()
    was fixed (PR #171) to tolerate a bear==base tie at the $0 negative-EPS price
    floor, but this SEPARATE validator (the actual Step-4 pre-persistence gate) has
    its own independent scenarioPrice ordering check with no such tolerance -- the
    same underlying bug recurring in a sibling script that doesn't share the fix."""

    def _projection_with_prices(self, bear_price, base_price, bull_price, bear_floored=False, base_floored=False):
        return {
            "ticker": "TEST", "id": "abc", "source": "AI_AGENT", "schemaVersion": "1.2",
            "version": 1, "savedAt": "2026-01-01T00:00:00Z", "rationale": "test",
            "snapshot": {"price": 10.0},
            "scenarios": {
                "bear": {"weight": 0.3, "growthRate": 5, "scenarioPrice": bear_price, "priceFloored": bear_floored},
                "base": {"weight": 0.4, "growthRate": 15, "scenarioPrice": base_price, "priceFloored": base_floored},
                "bull": {"weight": 0.3, "growthRate": 25, "scenarioPrice": bull_price},
            },
            "aiThesis": {"action": "HOLD"},
            "globalSettings": {},
        }

    def test_floored_tie_between_bear_and_base_is_allowed(self):
        proj = self._projection_with_prices(0.0, 0.0, 25.0, bear_floored=True, base_floored=True)
        errors = validate_projection(proj)
        assert not any("scenarioPrice" in e for e in errors)

    def test_non_floored_tie_is_still_rejected(self):
        """A tie NOT caused by the floor (e.g. two identical non-zero prices from
        a real input mistake) must still be caught -- the tolerance is scoped to
        the floor case only."""
        proj = self._projection_with_prices(50.0, 50.0, 80.0, bear_floored=False, base_floored=False)
        errors = validate_projection(proj)
        assert any("scenarioPrice" in e for e in errors)

    def test_genuine_inversion_still_rejected(self):
        proj = self._projection_with_prices(90.0, 50.0, 80.0)
        errors = validate_projection(proj)
        assert any("scenarioPrice" in e for e in errors)


def _base_projection(**overrides):
    """Helper for sector enum tests."""
    proj = {
        "ticker": "TEST", "id": "abc", "source": "AI_AGENT", "schemaVersion": "1.2",
        "version": 1, "savedAt": "2026-01-01T00:00:00Z", "rationale": "test",
        "snapshot": {"price": 100.0},
        "scenarios": {
            "bear": {"weight": 0.3, "growthRate": 5, "scenarioPrice": 80},
            "base": {"weight": 0.4, "growthRate": 15, "scenarioPrice": 100},
            "bull": {"weight": 0.3, "growthRate": 25, "scenarioPrice": 130},
        },
        "aiThesis": {"action": "HOLD"},
        "globalSettings": {},
    }
    proj.update(overrides)
    return proj


def test_valid_sector_enum_passes():
    proj = _base_projection(sector="chips_ai")
    errors = validate_projection(proj)
    assert not any("sector" in e for e in errors)


def test_invalid_sector_enum_fails():
    proj = _base_projection(sector="not_a_real_sector")
    errors = validate_projection(proj)
    assert any("sector" in e for e in errors)


class TestSnapshotRequiredFields:
    """Caught live 2026-08-28: AMAT's first-ever projection passed this validator
    (Step 4) with only snapshot.price/currency/exchange set, then was rejected by
    the real POST /api/projections endpoint (Step 6) for missing snapshot.shares,
    snapshot.revenue, and snapshot.lastActualPS — fields backend/src/utils/
    zod-schemas.ts's SnapshotSchema actually requires but this validator never
    checked. This validator's whole purpose is to catch schema violations BEFORE
    they reach the backend; a projection that passes here and fails there is
    exactly the bug this class guards against."""

    def _projection_with_snapshot(self, snapshot):
        return {
            "ticker": "TEST", "id": "abc", "source": "AI_AGENT", "schemaVersion": "1.2",
            "version": 1, "savedAt": "2026-01-01T00:00:00Z", "rationale": "test",
            "snapshot": snapshot,
            "scenarios": {
                "bear": {"weight": 0.3, "growthRate": 5, "scenarioPrice": 80},
                "base": {"weight": 0.4, "growthRate": 15, "scenarioPrice": 100},
                "bull": {"weight": 0.3, "growthRate": 25, "scenarioPrice": 130},
            },
            "aiThesis": {"action": "HOLD"},
            "globalSettings": {},
        }

    def test_missing_shares_revenue_lastActualPS_are_flagged(self):
        proj = self._projection_with_snapshot({"price": 100.0, "currency": "USD"})
        errors = validate_projection(proj)
        assert any("snapshot.shares" in e for e in errors)
        assert any("snapshot.revenue" in e for e in errors)
        assert any("snapshot.lastActualPS" in e for e in errors)

    def test_complete_snapshot_passes(self):
        proj = self._projection_with_snapshot({
            "price": 100.0, "currency": "USD", "shares": 1000, "revenue": 5000, "lastActualPS": 5.0,
        })
        errors = validate_projection(proj)
        assert not any("snapshot" in e for e in errors)

    def test_null_lastActualPS_is_allowed_key_must_exist(self):
        """Backend schema is .nullable().transform(v => v ?? 0) — null is a valid
        value, only a missing key is an error (pre-revenue/mining stocks, pitfall #5)."""
        proj = self._projection_with_snapshot({
            "price": 100.0, "currency": "USD", "shares": 1000, "revenue": 5000, "lastActualPS": None,
        })
        errors = validate_projection(proj)
        assert not any("snapshot.lastActualPS" in e for e in errors)


def test_missing_sector_is_not_an_error():
    proj = _base_projection()  # no "sector" key at all
    errors = validate_projection(proj)
    assert not any("sector" in e for e in errors)


class TestOutlookAuditVerification:
    """Gate test: Every stock valuation MUST include an outlookAudit verifying that
    the agent reviewed the last 2-4 earnings calls, verified guidance direction,
    and assessed backlog/pipeline before running DCF."""

    def _proj_with_audit(self, outlook_audit):
        proj = _base_projection()
        proj["snapshot"] = {
            "price": 100.0, "currency": "USD", "shares": 1000, "revenue": 5000, "lastActualPS": 5.0,
        }
        proj["analyticsLog"] = {"outlookAudit": outlook_audit}
        return proj

    def test_missing_outlook_audit_fails(self):
        proj = _base_projection()
        proj["snapshot"] = {
            "price": 100.0, "currency": "USD", "shares": 1000, "revenue": 5000, "lastActualPS": 5.0,
        }
        proj["analyticsLog"] = {}
        errors = validate_projection(proj)
        assert any("outlookAudit" in e for e in errors)

    def test_incomplete_outlook_audit_fails(self):
        # Missing callsAnalyzed or guidanceDirection
        incomplete = {
            "callsAnalyzed": [],
            "guidanceDirection": "RAISED",
            "strategicAssessment": "Some text",
        }
        errors = validate_projection(self._proj_with_audit(incomplete))
        assert any("callsAnalyzed" in e for e in errors)

    def test_placeholder_outlook_audit_fails(self):
        placeholder = {
            "callsAnalyzed": ["Q1", "Q2"],
            "guidanceDirection": "N/A",
            "strategicAssessment": "none",
        }
        errors = validate_projection(self._proj_with_audit(placeholder))
        assert any("guidanceDirection" in e for e in errors)

    def test_complete_valid_outlook_audit_passes(self):
        valid = {
            "callsAnalyzed": ["Q1 2026", "Q2 2026"],
            "guidanceDirection": "RAISED",
            "strategicAssessment": "FastPower platform backed by Siemens turbines and $2.4B Base Electron deal.",
            "adversarialRisks": ["Related-party customer credit", "Negative $85M cash burn"],
            "backlogPipeline": "$2.6B backlog, $14B pipeline",
        }
        errors = validate_projection(self._proj_with_audit(valid))
        assert not any("outlookAudit" in e for e in errors)

