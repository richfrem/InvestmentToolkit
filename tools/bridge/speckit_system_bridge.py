#!/usr/bin/env python3
"""
speckit_system_bridge.py
=====================================
Purpose:
    The "Universal Bridge" Synchronization Engine.
    Reads Spec Kitty definitions (Windsurf + Memory) and projects them into native
    configurations for:
    1.  Antigravity (.agent/)
    2.  Claude (.claude/)
    3.  Gemini (.gemini/)
    4.  GitHub Copilot (.github/)

    Philosophy:
    "Bring Your Own Agent" (BYOA). Maintain a Single Source of Truth in Spec Kitty,
    and auto-generate the necessary config files for any supported agent.

Usage:
    python tools/bridge/speckit_system_bridge.py
"""
import os
import shutil
from pathlib import Path
import re
import sys
import toml

# Force UTF-8 for Windows Consoles
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WINDSURF_DIR = PROJECT_ROOT / ".windsurf"
KITTIFY_DIR = PROJECT_ROOT / ".kittify"

# Targets
AGENT_DIR = PROJECT_ROOT / ".agent"
CLAUDE_DIR = PROJECT_ROOT / ".claude"
GEMINI_DIR = PROJECT_ROOT / ".gemini"
GITHUB_DIR = PROJECT_ROOT / ".github"

def setup_directories():
    """Ensure all target directory structures exist."""
    print(f"🔧 Initializing Target Directories...")
    
    # 1. Antigravity
    (AGENT_DIR / "rules").mkdir(parents=True, exist_ok=True)
    (AGENT_DIR / "workflows").mkdir(parents=True, exist_ok=True)
    
    # 2. Claude
    # Note: Sample uses .claude/commands/, but standard is often .claude/prompts/.
    # Following user's sample structure: .claude/commands/
    (CLAUDE_DIR / "commands").mkdir(parents=True, exist_ok=True)
    
    # 3. Gemini
    (GEMINI_DIR / "commands").mkdir(parents=True, exist_ok=True)
    
    # 4. Copilot
    (GITHUB_DIR / "prompts").mkdir(parents=True, exist_ok=True)

def ingest_rules():
    """Read rules from .kittify/memory (Source of Truth)."""
    rules = {}
    memory_dir = KITTIFY_DIR / "memory"
    
    if not memory_dir.exists():
        print("⚠️  No .kittify/memory directory found. Rules will be empty.")
        return rules
        
    for rule_file in sorted(memory_dir.rglob("*.md")):
        try:
            content = rule_file.read_text(encoding="utf-8")
            rules[rule_file.stem] = content
        except Exception as e:
            print(f"⚠️  Failed to read rule {rule_file.name}: {e}")
            
    return rules

def ingest_workflows():
    """Read workflows from .windsurf/workflows (Source of Truth)."""
    workflows = {}
    source_dir = WINDSURF_DIR / "workflows"
    
    if not source_dir.exists():
        print("⚠️  No .windsurf/workflows directory found. Workflows will be empty.")
        return workflows
        
    for wf_file in sorted(source_dir.rglob("*.md")):
        try:
            content = wf_file.read_text(encoding="utf-8")
            workflows[wf_file.name] = content # Key is full filename (spec-kitty.accept.md)
        except Exception as e:
            print(f"⚠️  Failed to read workflow {wf_file.name}: {e}")
            
    return workflows

def sync_antigravity(workflows, rules):
    """Sync to .agent/ (Antigravity)."""
    print("\n🔵 Syncing Antigravity (.agent)...")
    
    # Rules (e.g., constitution.md)
    for name, content in rules.items():
        (AGENT_DIR / "rules" / f"{name}.md").write_text(content, encoding="utf-8")
        
    # Workflows (Direct Copy, maybe ensure actor is consistent)
    for filename, content in workflows.items():
        # Keep --actor "windsurf" or change to "antigravity"? 
        # User said "antigravity was based on windsurf". Let's stick to 'antigravity' for clarity in .agent
        # But if the CLI tool expects 'windsurf', this might break. 
        # Safest bet: Replace "windsurf" with "antigravity" for the .agent folder.
        fixed_content = content.replace('--actor "windsurf"', '--actor "antigravity"')
        (AGENT_DIR / "workflows" / filename).write_text(fixed_content, encoding="utf-8")
        
    print(f"   ✅ Synced {len(rules)} rules and {len(workflows)} workflows.")

def sync_claude(workflows, rules):
    """Sync to .claude/."""
    print("\n🟠 Syncing Claude (.claude)...")
    
    # 1. Context (CLAUDE.md)
    claude_md = CLAUDE_DIR / "CLAUDE.md"
    content = ["# Claude Assistant Instructions\n"]
    content.append("Managed by Spec Kitty Bridge.\n\n")
    
    for name, rule_text in rules.items():
        content.append(f"## {name}\n\n{rule_text}\n\n---\n\n")
        
    claude_md.write_text("".join(content), encoding="utf-8")
    
    # 2. Commands/Prompts (.claude/commands/*.md)
    # Using 'commands' dir based on sample provided
    count = 0
    for filename, text in workflows.items():
        fixed_text = text.replace('--actor "windsurf"', '--actor "claude"')
        (CLAUDE_DIR / "commands" / filename).write_text(fixed_text, encoding="utf-8")
        count += 1
        
    print(f"   ✅ Generated CLAUDE.md and {count} commands.")

def sync_gemini(workflows, rules):
    """Sync to .gemini/."""
    print("\n✨ Syncing Gemini (.gemini)...")
    
    # 1. Context (GEMINI.md)
    gemini_md = GEMINI_DIR / "GEMINI.md"
    # Note: Gemini often looks for GEMINI.md in Project Root, not .gemini/GEMINI.md
    # Current script logic put it in Project Root. Let's stick to that for compatibility.
    root_gemini_md = PROJECT_ROOT / "GEMINI.md"
    
    content = ["# Gemini CLI Instructions\n"]
    content.append("Managed by Spec Kitty Bridge.\n\n")
    
    for name, rule_text in rules.items():
        content.append(f"## {name}\n\n{rule_text}\n\n---\n\n")
        
    root_gemini_md.write_text("".join(content), encoding="utf-8")
    
    # 2. Commands (.gemini/commands/*.toml)
    count = 0
    for filename, text in workflows.items():
        stem = filename.replace(".md", "") # remove .md
        
        # Extract description
        description = f"Executes {stem}"
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                fm = text[3:end]
                for line in fm.split("\n"):
                    if line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"')
                        break
                        
        # Formatting
        description = description.replace('"', '\\"')
        fixed_text = text.replace('--actor "windsurf"', '--actor "gemini"')
        fixed_text = fixed_text.replace('$ARGUMENTS', '{{args}}')
        fixed_text = fixed_text.replace('(Missing script command for sh)', 'spec-kitty') # Attempt fix
        
        toml_content = f'description = "{description}"\n\nprompt = """\n{fixed_text}\n"""\n'
        
        (GEMINI_DIR / "commands" / f"{stem}.toml").write_text(toml_content, encoding="utf-8")
        count += 1
        
    print(f"   ✅ Generated GEMINI.md and {count} commands.")

def sync_copilot(workflows, rules):
    """Sync to .github/ (Copilot)."""
    print("\n🤖 Syncing Copilot (.github)...")
    
    # 1. Instructions (copilot-instructions.md)
    instr_file = GITHUB_DIR / "copilot-instructions.md"
    content = ["# Copilot Instructions\n"]
    content.append("> Managed by Spec Kitty Bridge.\n\n")
    
    for name, rule_text in rules.items():
        content.append(f"## Rule: {name}\n\n{rule_text}\n\n---\n\n")
        
    # Index Workflows
    content.append("\n# Available Workflows\n")
    for filename in workflows.keys():
        stem = filename.replace(".md", "")
        content.append(f"- /prompts/{stem}.prompt.md\n")

    instr_file.write_text("".join(content), encoding="utf-8")
    
    # 2. Prompts (.github/prompts/*.prompt.md)
    count = 0
    for filename, text in workflows.items():
        stem = filename.replace(".md", "")
        fixed_text = text.replace('--actor "windsurf"', '--actor "copilot"')
        
        # Wrap in comment? Or just raw? Sample showed raw content but with .prompt.md extension
        # target_filename = f"{stem}.prompt.md"
        # Actually sample was: spec-kitty.accept.prompt.md
        # If input is spec-kitty.accept.md, then output is spec-kitty.accept.prompt.md
        
        target_file = GITHUB_DIR / "prompts" / f"{stem}.prompt.md"
        
        # Make sure to include the original frontmatter? Yes.
        target_file.write_text(fixed_text, encoding="utf-8")
        count += 1
        
    print(f"   ✅ Generated copilot-instructions.md and {count} prompts.")

def main():
    print("🚀 Starting Spec Kitty Bridge Sync...")
    
    setup_directories()
    
    # 1. Ingest Source (Spec Kitty)
    rules = ingest_rules()
    workflows = ingest_workflows()
    
    if not workflows and not rules:
        print("❌ No source data found in .windsurf or .kittify. Run 'spec-kitty init' first.")
        return

    # 2. Project to All Agents
    sync_antigravity(workflows, rules)
    sync_claude(workflows, rules)
    sync_gemini(workflows, rules)
    sync_copilot(workflows, rules)
    
    print("\n🎉 Bridge Sync Complete. All agents are configured.")

if __name__ == "__main__":
    main()
