#!/usr/bin/env python3
"""
repo_root.py — locate the InvestmentToolkit repository root from any script location.

Purpose:
    The one way portfolio-advisor scripts find repo-level state (context/, temp/,
    investment_screener/). Works from the canonical plugins/portfolio-advisor/scripts/,
    from a skill spoke (plugins/.../skills/<skill>/scripts/) and from an installed hard
    copy (.agents/skills/<skill>/scripts/). Replaces fixed-depth Path(__file__).parents[3],
    which only worked from the canonical folder, and update_targets' private copy.

Layer:
    plugins/portfolio-advisor/scripts (shared helper; linked into skills via symlink_manager)

Usage:
    from repo_root import find_repo_root
    REPO_ROOT = find_repo_root(Path(__file__))

Key Functions (Index):
    - find_repo_root(start) - nearest ancestor containing investment_screener/

Key Input Dependencies:
    None (standard library only)
"""
from pathlib import Path

REPO_MARKER = "investment_screener"


class RepoRootNotFound(RuntimeError):
    """Raised when no ancestor of the start path contains the repo marker."""


def find_repo_root(start: Path) -> Path:
    """Return the nearest ancestor of `start` containing the investment_screener/ folder.

    Args:
        start: A file or directory inside the repository (usually Path(__file__)).

    Returns:
        The repository root.

    Raises:
        RepoRootNotFound: if no ancestor contains investment_screener/ — never guesses a depth.
    """
    start = Path(start).absolute()
    for candidate in [start, *start.parents]:
        if (candidate / REPO_MARKER).is_dir():
            return candidate
    raise RepoRootNotFound(f"No '{REPO_MARKER}/' folder above {start}; run from inside the InvestmentToolkit repo.")
