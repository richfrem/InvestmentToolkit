"""Purpose: enforce AI forward-evidence gates across valuation and review skills.

Layer: Workflow contracts. Key Functions: skill, guide and sweep-template checks.
Key Input Dependencies: eight source SKILL.md files, shared guide, sweep templates.
"""
from pathlib import Path
import json

import pytest

ROOT = Path(__file__).resolve().parents[3]
SKILLS = (
    ("stock-valuation", "update-stock-analysis"),
    ("stock-valuation", "stock-research"),
    ("stock-valuation", "forward-valuation-challenge"),
    ("portfolio-advisor", "daily-loop"),
    ("portfolio-advisor", "news-sweep"),
    ("portfolio-advisor", "stock-intake"),
    ("portfolio-advisor", "strategic-review"),
    ("portfolio-advisor", "weekly-review"),
)


@pytest.mark.parametrize("skill", ("update-stock-analysis", "stock-research"))
def test_rate_protocol_is_packaged_as_one_managed_reference(skill: str) -> None:
    """Both distributed skills must resolve the same authoritative procedure."""
    source = "plugins/stock-valuation/references/valuation-method-and-discount-rate.md"
    destination = f"plugins/stock-valuation/skills/{skill}/references/valuation-method-and-discount-rate.md"
    link = ROOT / destination
    assert link.is_symlink()
    assert link.resolve() == ROOT / source
    assert link.is_file()
    manifest = json.loads((ROOT / "symlinks.json").read_text())
    assert any(entry["src"] == source and entry["dst"] == destination for entry in manifest["links"])
    cases = json.loads((ROOT / f"plugins/stock-valuation/skills/{skill}/evals/evals.json").read_text())
    assert len({case["id"] for case in cases}) == len(cases)


@pytest.mark.parametrize("plugin,skill", SKILLS)
def test_skill_requires_forward_evidence_before_recommendation(plugin: str, skill: str) -> None:
    """Each entry point must enforce and package the same evidence gate."""
    folder = ROOT / "plugins" / plugin / "skills" / skill
    text = (folder / "SKILL.md").read_text()
    assert "AI forward-evidence gate" in text
    assert "references/ai-forward-valuation.md" in text
    guide = folder / "references/ai-forward-valuation.md"
    assert guide.resolve() == ROOT / "plugins/stock-valuation/references/ai-forward-valuation.md"
    assert guide.is_file()


def test_shared_guide_covers_memory_power_cashflows_and_review_readiness() -> None:
    """Forward demand needs dated evidence and a cash-flow bridge, not slogans."""
    guide = (ROOT / "plugins/stock-valuation/references/ai-forward-valuation.md").read_text()
    for requirement in ("HBM", "DDR", "NAND", "SSD", "KV-cache", "time-to-power",
                        "capex", "working capital", "forward EPS", "NEEDS_REVALUATION",
                        "terminal", "primary sources", "non-cancellable"):
        assert requirement in guide


def test_capacity_build_precedes_rate_and_rate_needs_written_rationale() -> None:
    """Infrastructure names get a dated capacity-to-earnings build before any rate is applied."""
    guide = (ROOT / "plugins/stock-valuation/references/ai-forward-valuation.md").read_text()
    for requirement in ("Capacity-to-earnings build", "before selecting a discount rate",
                        "recurring", "fit-out", "per MW", "contracted floor", "energized",
                        "unfunded", "common shareholders"):
        assert requirement in guide
    protocol = (ROOT / "plugins/stock-valuation/references/valuation-method-and-discount-rate.md").read_text()
    assert '"rationale"' in protocol and "Why this rate" in protocol
    skill = (ROOT / "plugins/stock-valuation/skills/update-stock-analysis/SKILL.md").read_text()
    assert skill.index("capacity-to-earnings build") < skill.index("wacc.py --inputs")


@pytest.mark.parametrize("period", ("daily", "weekly"))
def test_generated_sweep_instructions_request_forward_evidence(period: str) -> None:
    """Generated prompts must carry the gate rather than relying on chat context."""
    text = (ROOT / f"plugins/portfolio-advisor/assets/templates/{period}_sweep.md.template").read_text()
    for requirement in ("AI forward-evidence gate", "DDR", "NAND", "SSD", "time-to-power",
                        "forward EPS", "capex", "NEEDS_REVALUATION"):
        assert requirement in text
