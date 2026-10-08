"""Purpose: every review and valuation skill follows one recommendation-coherence procedure.

Layer: Workflow contracts. Key Functions: packaged-reference and guide-content checks.
Key Input Dependencies: six source SKILL.md files, the shared guide, symlinks.json.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "plugins/portfolio-advisor/references/recommendation-coherence.md"
SKILLS = (
    ("portfolio-advisor", "daily-loop"), ("portfolio-advisor", "weekly-review"),
    ("portfolio-advisor", "strategic-review"), ("portfolio-advisor", "stock-intake"),
    ("stock-valuation", "update-stock-analysis"), ("stock-valuation", "stock-research"),
)


@pytest.mark.parametrize("plugin,skill", SKILLS)
def test_skill_links_the_one_shared_procedure(plugin: str, skill: str) -> None:
    """Each entry point routes to the same guide through a managed link."""
    folder = ROOT / "plugins" / plugin / "skills" / skill
    assert "references/recommendation-coherence.md" in (folder / "SKILL.md").read_text()
    link = folder / "references/recommendation-coherence.md"
    assert link.is_symlink() and link.resolve() == ROOT / SOURCE
    manifest = json.loads((ROOT / "symlinks.json").read_text())
    destination = f"plugins/{plugin}/skills/{skill}/references/recommendation-coherence.md"
    assert any(entry["src"] == SOURCE and entry["dst"] == destination for entry in manifest["links"])


def test_guide_covers_trades_decisions_priorities_and_chart_levels() -> None:
    """The procedure names the canonical fields and scripts rather than describing them loosely."""
    guide = (ROOT / SOURCE).read_text()
    for requirement in ("tv-portfolio-sync", "QUESTRADE_ENABLED", "recent_trades", "decision_check",
                        "set_standing_decision.py", "CONFLICT", "OUTDATED", "Already acted on",
                        "200 EMA", "ta_staleness_days", "refresh_all.py --publish"):
        assert requirement in guide
