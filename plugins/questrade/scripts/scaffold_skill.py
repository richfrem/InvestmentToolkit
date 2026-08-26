#!/usr/bin/env python3
"""
scaffold_skill.py - Questrade skill scaffolder.

Purpose:
    Generates a new plugins/questrade/skills/<name>/SKILL.md from the canonical
    template (assets/templates/SKILL.md.template), pre-wired to point at the
    hub-and-spoke schema reference instead of letting an agent re-derive or
    hand-write MCP param names from memory (the root cause of prior drift
    between order-draft's SKILL.md and the live API). Also creates the skill's
    evals/ dir and registers + creates the schema-reference symlink via
    symlink_manager.py (never raw ln -s, per symlink-cross-platform.md).

Layer:
    Plugin Tooling / Questrade

Usage Examples:
    python3 scripts/scaffold_skill.py \\
        --slug questrade-cancel-order \\
        --description "Cancel a working Questrade order via MCP." \\
        --purpose "Cancels a pending order instruction after user confirmation." \\
        --schema-section "create_order_instruction (cancel)" \\
        --argument-hint "[order_id]"

Key Functions (Index):
    - render_template(values) - Fill the SKILL.md template with provided values
    - scaffold(args) - Create skill dir, write SKILL.md, wire the schema symlink

Key Input Dependencies:
    - plugins/questrade/assets/templates/SKILL.md.template (canonical template)
    - plugins/questrade/references/questrade-tool-schemas.md (symlink target)

Key Output Dependencies:
    - plugins/questrade/skills/<slug>/SKILL.md
    - plugins/questrade/skills/<slug>/evals/ (empty, for future eval authoring)
    - symlinks.json (new manifest entry via symlink_manager.py create)
"""

import argparse
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PLUGIN_ROOT.parent.parent
TEMPLATE_PATH = PLUGIN_ROOT / "assets" / "templates" / "SKILL.md.template"
SYMLINK_MANAGER = REPO_ROOT / ".agents" / "skills" / "symlink-manager" / "scripts" / "symlink_manager.py"


def render_template(values: dict[str, str]) -> str:
    """Fill the SKILL.md template with the provided placeholder values."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def scaffold(args: argparse.Namespace) -> Path:
    """Create the skill directory, write SKILL.md, and wire the schema symlink."""
    skill_dir = PLUGIN_ROOT / "skills" / args.slug
    if skill_dir.exists():
        print(f"✗ {skill_dir} already exists — aborting to avoid overwrite.", file=sys.stderr)
        sys.exit(1)

    skill_dir.mkdir(parents=True)
    (skill_dir / "evals").mkdir()

    skill_slug = args.slug.removeprefix("questrade-")
    values = {
        "skill_slug": skill_slug,
        "title": args.title or skill_slug.replace("-", " ").title(),
        "description": args.description,
        "argument_hint": args.argument_hint or "[]",
        "purpose": args.purpose,
        "schema_section": args.schema_section,
        "workflow": args.workflow or "1. TODO: describe the call sequence.\n2. TODO: describe output formatting.",
    }
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(render_template(values), encoding="utf-8")
    print(f"✓ Wrote {skill_md.relative_to(REPO_ROOT)}")

    subprocess.run(
        [
            sys.executable,
            str(SYMLINK_MANAGER),
            "create",
            "--src",
            "plugins/questrade/references/questrade-tool-schemas.md",
            "--dst",
            f"plugins/questrade/skills/{args.slug}/references/questrade-tool-schemas.md",
            "--description",
            f"Hub-and-spoke symlink for canonical Questrade MCP tool schemas in {args.slug} skill",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    print(f"\nNext: fill in the '## Workflow' and any '## Skill-Specific Behavior' section in {skill_md.name} by hand.")
    return skill_md


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Scaffold a new questrade skill from the canonical template.")
    parser.add_argument("--slug", required=True, help="Skill directory name, e.g. questrade-cancel-order")
    parser.add_argument("--description", required=True, help="One-line SKILL.md frontmatter description")
    parser.add_argument("--purpose", required=True, help="## Purpose section body")
    parser.add_argument("--schema-section", required=True, help="Which references/questrade-tool-schemas.md section this skill relies on")
    parser.add_argument("--title", help="H1 title (defaults to a title-cased slug)")
    parser.add_argument("--argument-hint", help="argument-hint frontmatter value")
    parser.add_argument("--workflow", help="## Workflow section body (numbered steps); left as TODO if omitted")
    args = parser.parse_args()
    scaffold(args)


if __name__ == "__main__":
    main()
