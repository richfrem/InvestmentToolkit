"""
test_pine_advisor_skill.py — Verify the tv_pine_advisor skill file exists and is correctly configured.
"""

import os


def test_pine_advisor_skill_exists_and_configured():
    skill_path = ".agents/skills/tv_pine_advisor/SKILL.md"
    assert os.path.exists(skill_path), f"Skill file missing: {skill_path}"

    with open(skill_path) as f:
        content = f.read()

    assert "/pine-analyze" in content, "Missing /pine-analyze trigger"
    assert "tv_pine_manager.py" in content, "Missing tv_pine_manager.py reference"
