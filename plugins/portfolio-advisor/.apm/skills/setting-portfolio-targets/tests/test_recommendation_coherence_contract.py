"""Purpose: every review and valuation mode follows one recommendation-coherence procedure.

Layer: Workflow contracts. Key Functions: mode-file link and guide-content checks.
Key Input Dependencies: portfolio-advisor mode files and the shared guide.
"""
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "investment_screener").is_dir())
HUBS = ROOT / "plugins/portfolio-advisor/.apm/skills"
SOURCE = HUBS / "setting-portfolio-targets/references/recommendation-coherence.md"
MODES = (
    ("running-portfolio-reviews", "daily-loop"), ("running-portfolio-reviews", "weekly-review"),
    ("setting-portfolio-targets", "strategic-review"), ("valuing-investments", "stock-intake"),
    ("valuing-investments", "update-analysis"), ("valuing-investments", "research-sweep"),
)


@pytest.mark.parametrize("hub,mode", MODES)
def test_mode_links_the_one_shared_procedure(hub: str, mode: str) -> None:
    """Each entry point links the single guide, and the link resolves to a real file."""
    mode_file = HUBS / hub / "references/modes" / f"{mode}.md"
    links = [t for t in __import__("re").findall(r"\]\(([^)#]*recommendation-coherence\.md)", mode_file.read_text())]
    assert links, f"{mode_file} does not link recommendation-coherence.md"
    for link in links:
        target = (mode_file.parent / link).resolve()
        assert target == SOURCE.resolve() and not target.is_symlink()


def test_guide_is_a_single_real_file() -> None:
    """Exactly one copy exists and it is not a symlink."""
    copies = list(HUBS.rglob("recommendation-coherence.md"))
    assert copies == [SOURCE] and not SOURCE.is_symlink()


def test_guide_covers_trades_decisions_priorities_and_chart_levels() -> None:
    """The procedure names the canonical fields and scripts rather than describing them loosely."""
    guide = SOURCE.read_text()
    for requirement in ("tv-portfolio-sync", "QUESTRADE_ENABLED", "recent_trades", "decision_check",
                        "set_standing_decision.py", "CONFLICT", "OUTDATED", "Already acted on",
                        "200 EMA", "ta_staleness_days", "refresh_all.py --publish",
                        "CONFIRMED", "decision_condition", "refreshFirst", "/update-stock-analysis"):
        assert requirement in guide
