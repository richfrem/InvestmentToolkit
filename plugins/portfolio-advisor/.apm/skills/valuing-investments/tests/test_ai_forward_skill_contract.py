"""Purpose: enforce AI forward-evidence gates across valuation and review skills.

Layer: Workflow contracts. Key Functions: skill, guide and sweep-template checks.
Key Input Dependencies: eight mode files, the shared guide, the sweep templates.
"""
from pathlib import Path
import json
import re

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
PLUGIN = ROOT / "plugins/portfolio-advisor"
SKILLS_DIR = PLUGIN / ".apm/skills"
GUIDE = SKILLS_DIR / "valuing-investments/references/ai-forward-valuation.md"
RATE_PROTOCOL = SKILLS_DIR / "valuing-investments/references/valuation-method-and-discount-rate.md"
# (hub, mode) entry points that must enforce the AI forward-evidence gate
MODES = (
    ("valuing-investments", "update-analysis"),
    ("valuing-investments", "research-sweep"),
    ("valuing-investments", "forward-challenge"),
    ("running-portfolio-reviews", "daily-loop"),
    ("running-portfolio-reviews", "news-sweep"),
    ("valuing-investments", "stock-intake"),
    ("setting-portfolio-targets", "strategic-review"),
    ("running-portfolio-reviews", "weekly-review"),
)


def _mode(hub: str, mode: str) -> Path:
    return SKILLS_DIR / hub / "references/modes" / f"{mode}.md"


def _linked(mode_file: Path, filename: str) -> list[Path]:
    """Every markdown link in a mode file that targets `filename`, resolved from the file's own folder."""
    targets = re.findall(r"\]\(([^)\s#]*" + re.escape(filename) + r")", mode_file.read_text())
    return [(mode_file.parent / t).resolve() for t in targets]


@pytest.mark.parametrize("mode", ("update-analysis", "research-sweep"))
def test_rate_protocol_is_one_managed_reference_that_both_modes_link_to(mode: str) -> None:
    """The rate protocol exists once, with no copies or links, and both valuation modes resolve to it."""
    copies = [p for p in PLUGIN.rglob("valuation-method-and-discount-rate.md") if ".pytest_cache" not in str(p)]
    assert copies == [RATE_PROTOCOL]
    assert not any(p.is_symlink() for p in PLUGIN.rglob("*"))
    assert RATE_PROTOCOL.resolve() in _linked(_mode("valuing-investments", mode), "valuation-method-and-discount-rate.md")
    cases = json.loads((SKILLS_DIR / "valuing-investments/evals/evals.json").read_text())
    assert len({case.get("id", case.get("name")) + case["mode"] for case in cases}) == len(cases)


@pytest.mark.parametrize("hub,mode", MODES)
def test_mode_requires_forward_evidence_before_recommendation(hub: str, mode: str) -> None:
    """Each entry point must enforce the same evidence gate and link to the one shared guide."""
    mode_file = _mode(hub, mode)
    assert "AI forward-evidence gate" in mode_file.read_text()
    assert GUIDE.resolve() in _linked(mode_file, "ai-forward-valuation.md")
    assert GUIDE.is_file()


def test_shared_guide_covers_memory_power_cashflows_and_review_readiness() -> None:
    """Forward demand needs dated evidence and a cash-flow bridge, not slogans."""
    guide = (ROOT / "plugins/portfolio-advisor/.apm/skills/valuing-investments/references/ai-forward-valuation.md").read_text()
    for requirement in ("HBM", "DDR", "NAND", "SSD", "KV-cache", "time-to-power",
                        "capex", "working capital", "forward EPS", "NEEDS_REVALUATION",
                        "terminal", "primary sources", "non-cancellable"):
        assert requirement in guide


def test_capacity_build_precedes_rate_and_rate_needs_written_rationale() -> None:
    """Infrastructure names get a dated capacity-to-earnings build before any rate is applied."""
    guide = (ROOT / "plugins/portfolio-advisor/.apm/skills/valuing-investments/references/ai-forward-valuation.md").read_text()
    for requirement in ("Capacity-to-earnings build", "before selecting a discount rate",
                        "recurring", "fit-out", "per MW", "contracted floor", "energized",
                        "unfunded", "common shareholders"):
        assert requirement in guide
    protocol = (ROOT / "plugins/portfolio-advisor/.apm/skills/valuing-investments/references/valuation-method-and-discount-rate.md").read_text()
    assert '"rationale"' in protocol and "Why this rate" in protocol
    skill = (ROOT / "plugins/portfolio-advisor/.apm/skills/valuing-investments/references/modes/update-analysis.md").read_text()
    assert skill.index("capacity-to-earnings build") < skill.index("wacc.py --inputs")


@pytest.mark.parametrize("period", ("daily", "weekly"))
def test_generated_sweep_instructions_request_forward_evidence(period: str) -> None:
    """Generated prompts must carry the gate rather than relying on chat context."""
    text = (ROOT / f"plugins/portfolio-advisor/.apm/skills/running-portfolio-reviews/assets/templates/{period}_sweep.md.template").read_text()
    for requirement in ("AI forward-evidence gate", "DDR", "NAND", "SSD", "time-to-power",
                        "forward EPS", "capex", "NEEDS_REVALUATION"):
        assert requirement in text
