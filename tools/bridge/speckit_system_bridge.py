#!/usr/bin/env python3
"""
speckit_system_bridge.py
=====================================
Purpose:
    The "Dual Tri Bridge" Synchronization Engine.
    Projects the Single Source of Truth (.agent/) into native configurations for:
    1. Gemini CLI (.gemini/)
    2. VS Code Copilot (.github/)

    This script ensures that all 3 personas (Antigravity, Gemini, Copilot) share
    the exact same Rules and Workflows without manual duplication.

Functions:
    1. Mirrors .agent/rules/ -> .gemini/rules/
    2. Generates .gemini/commands/*.toml from .agent/workflows/*.md

Usage:
    python tools/bridge/gemini_sync.py
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
    pass  # Python < 3.7 or weird env

# Platform Compatibility

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_DIR = PROJECT_ROOT / ".agent"
GEMINI_DIR = PROJECT_ROOT / ".gemini"
GITHUB_DIR = PROJECT_ROOT / ".github"

def setup_directories():
    """Ensure target .gemini and .github structure exists."""
    print(f"🔧 Initializing Gemini Bridge...")
    
    # Create directories if missing
    (GEMINI_DIR / "rules").mkdir(parents=True, exist_ok=True)
    (GEMINI_DIR / "commands").mkdir(parents=True, exist_ok=True)
    GITHUB_DIR.mkdir(parents=True, exist_ok=True)
    (GITHUB_DIR / "prompts").mkdir(parents=True, exist_ok=True)

import stat
def handle_remove_readonly(func, path, exc):
    """Error handler for shutil.rmtree to clean read-only files (Windows fix)."""
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == 13: # EACCES
        os.chmod(path, stat.S_IWRITE)
        func(path)
    else:
        raise

def normalize_paths(content: str, direction: str) -> str:
    """
    Rewrites relative links in Markdown content to match the target environment.
    
    Args:
        content: The raw markdown content.
        direction: 'upstream_to_core' or 'core_to_downstream'
    
    Returns:
        Content with fixed links.
    """
    if direction == 'upstream_to_core':
        # Spec Kitty (.kittify) -> Antigravity (.agent)
        # 1. /memory/ -> .agent/rules/
        content = content.replace("/memory/", ".agent/rules/")
        
        # 2. .kittify/missions/ -> .agent/workflows/
        content = content.replace(".kittify/missions/", ".agent/workflows/")
        
        # 3. .kittify/ -> .agent/
        content = content.replace(".kittify/", ".agent/")
        
        # 4. Standardize /docs to docs/
        content = content.replace("/docs/", "docs/")
        
        # 5. Handle relative parent traverse (../../memory)
        content = content.replace("../memory/", ".agent/rules/")

    elif direction == 'core_to_downstream':
        # Antigravity (.agent) -> Gemini/Copilot
        # For Gemini TOML, links usually stay relative to project root or use absolute anchors
        # Here we mostly ensure .agent/ paths are preserved or simplified
        pass

    return content

def sync_from_upstream():
    """Ingest artifacts from upstream Spec Kitty repo (.windsurf)."""
    print("🌊 Checking for Upstream Sources (Spec Kitty/Windsurf)...")
    
    # 1. Identify Source (.windsurf is created by `spec-kitty init`)
    windsurf_dir = PROJECT_ROOT / ".windsurf"
    kittify_dir = PROJECT_ROOT / ".kittify"
    
    if not windsurf_dir.exists():
        print("   ⚠️  No .windsurf directory found. Run 'spec-kitty init . --ai windsurf' first.")
        return
    
    print(f"   ✅ Found Upstream Source: {windsurf_dir}")

    # 2. Sync Workflows (.windsurf/workflows/*.md -> .agent/workflows/)
    # Spec Kitty creates symlinks here; we copy their content (resolves symlinks)
    workflow_source = windsurf_dir / "workflows"
    workflow_target = AGENT_DIR / "workflows"
    workflow_target.mkdir(exist_ok=True, parents=True)

    if workflow_source.exists():
        count = 0
        for item in workflow_source.glob("*.md"):
            # Read content (resolves symlinks automatically)
            try:
                raw_content = item.read_text(encoding="utf-8")
                fixed_content = normalize_paths(raw_content, 'upstream_to_core')
                
                # Write to .agent/workflows/ (preserve original name, e.g., spec-kitty.accept.md)
                target_path = workflow_target / item.name
                target_path.write_text(fixed_content, encoding="utf-8")
                print(f"   📥 Ingested Workflow: {item.name}")
                count += 1
            except Exception as e:
                print(f"   ⚠️  Failed to ingest {item.name}: {e}")
        print(f"   ✅ Synced {count} workflows from .windsurf")
    else:
        print("   ⚠️  No .windsurf/workflows directory found.")



    print("   ✅ Upstream Ingest Complete.")

def sync_instructions():
    """Sync Rules/Instructions to GEMINI.md (Context) and Copilot (Prompt)."""
    print("📜 Syncing Instructions (Rules as Context)...")
    source_rules = AGENT_DIR / "rules"
    target_gemini_rules_link = GEMINI_DIR / "rules"
    
    # 1. Cleanup Legacy Symlink (Gemini 3 Policy Engine Confusion)
    # in Gem3, .gemini/* is for TOML Policies. Our Rules are Markdown Instructions.
    if target_gemini_rules_link.exists() or target_gemini_rules_link.is_symlink():
        print("🧹 Removing legacy .gemini/rules symlink (Rules are now injected into GEMINI.md)")
        try:
            if target_gemini_rules_link.is_symlink() or target_gemini_rules_link.is_file():
                target_gemini_rules_link.unlink()
            else:
                shutil.rmtree(target_gemini_rules_link)
        except Exception as e:
             print(f"⚠️  Could not clean .gemini/rules: {e}")

    if not source_rules.exists():
        print("⚠️  No .agent/rules directory found. Skipping generation.")
        return

    # 2. Update GEMINI.md (The Root Context for Gemini CLI)
    gemini_md = PROJECT_ROOT / "GEMINI.md"
    gemini_content = ["# Gemini CLI Instructions\n"]
    gemini_content.append("Managed by Antigravity System Sync.\n")
    gemini_content.append("Configuration Sources:\n")
    gemini_content.append("*   **Rules:** Injected below (Source: `.agent/rules/`)\n")
    gemini_content.append("*   **Workflows:** `.agent/workflows/`\n\n")
    
    gemini_content.append("# System Rules & Policies\n\n")
    
    # Ingest all rules
    rule_files = sorted(source_rules.rglob("*.md"))
    for rule in rule_files:
        try:
            text = rule.read_text(encoding="utf-8")
            gemini_content.append(f"## {rule.stem}\n\n{text}\n\n---\n\n")
        except Exception as e:
            print(f"⚠️ Failed to read rule {rule.name}: {e}")

    gemini_md.write_text("".join(gemini_content), encoding="utf-8")
    print(f"✅ Injected {len(rule_files)} rules into GEMINI.md")

    # 3. Update Copilot Context
    generate_copilot_instructions(source_rules)
    generate_copilot_prompts()
    sync_project_memory()

def generate_copilot_prompts():
    """Generates .github/prompts/*.prompt.md for each workflow."""
    print("🤖 Generating Copilot Modular Prompts...")
    source_workflows = AGENT_DIR / "workflows"
    target_prompts = GITHUB_DIR / "prompts"
    
    if not source_workflows.exists():
        return

    count = 0
    # RECURSIVE: Find workflows in subfolders too
    for workflow_file in source_workflows.rglob("*.md"):
        # Create a prompt file that Copilot can reference
        target_file = target_prompts / f"{workflow_file.stem}.prompt.md"
        
        try:
            content = workflow_file.read_text(encoding="utf-8")
            prompt_content = f"""<!-- Auto-generated from .agent/workflows/{workflow_file.name} -->
{content}
"""
            target_file.write_text(prompt_content, encoding="utf-8")
            count += 1
        except Exception as e:
            print(f"❌ Failed to generate prompt for {workflow_file.name}: {e}")
            
    print(f"✅ Generated {count} Copilot prompt files.")

def generate_copilot_instructions(source_rules_dir):
    """Concatenate all rules into .github/copilot-instructions.md for VS Code."""
    print("🤖 Generating Copilot Instructions...")
    
    copilot_file = GITHUB_DIR / "copilot-instructions.md"
    
    content = ["# Oracle Forms Analysis - Copilot Instructions\n\n"]
    content.append("> **Auto-Generated**: Do not edit. Update .agent/rules/ instead.\n\n")
    
    # RECURSIVE sort
    for rule_file in sorted(source_rules_dir.rglob("*.md")):
        # Skip Constitution (Mirrored as file to .kittify/memory/ instead of context injection)
        if rule_file.name.lower() == "constitution.md":
            continue

        try:
            rule_content = rule_file.read_text(encoding="utf-8")
            content.append(f"## Rule: {rule_file.stem}\n\n")
            content.append(rule_content)
            content.append("\n\n---\n\n")
        except Exception as e:
            print(f"⚠️ Failed to read {rule_file.name}: {e}")
            
    copilot_file.write_text("".join(content), encoding="utf-8")
    print(f"✅ Updated {copilot_file}")

    # Index Workflows for Copilot
    inventory_content = ["\n\n# Available Workflows (CLI Commands)\n\n"]
    inventory_content.append("Use `gemini run <name>` or `/workflow-start <name>` to execute these:\n\n")
    
    workflows_dir = AGENT_DIR / "workflows"
    if workflows_dir.exists():
        for wf in sorted(workflows_dir.rglob("*.md")):
            inventory_content.append(f"- **{wf.stem}**: (See .agent/workflows/{wf.name})\n")
            
    with open(copilot_file, "a", encoding="utf-8") as f:
        f.write("".join(inventory_content))
    print(f"✅ Indexed workflows in {copilot_file}")


def create_gemini_root_doc():
    """Create the master GEMINI.md instruction file."""
    content = """# Gemini CLI Instructions
Managed by Antigravity System Sync.
Configuration Sources:
*   **Rules:** `.agent/rules/`
*   **Workflows:** `.agent/workflows/`
"""
    (PROJECT_ROOT / "GEMINI.md").write_text(content, encoding="utf-8")
    print("📝 Updated GEMINI.md root instruction.")

def sync_skills():
    """Mirror skills from .agent/skills to .gemini/skills via Symlink."""
    print("🧠 Syncing Skills...")
    source_skills = AGENT_DIR / "skills"
    target_skills = GEMINI_DIR / "skills"
    
    if not source_skills.exists():
        print("⚠️  No .agent/skills directory found. Skipping.")
        return
        
    if target_skills.exists() or target_skills.is_symlink():
        try:
            if target_skills.is_symlink() or target_skills.is_file():
                target_skills.unlink()
            else:
                shutil.rmtree(target_skills, onerror=handle_remove_readonly)
        except Exception as e:
            print(f"⚠️  Could not clean .gemini/skills: {e}")

    try:
        shutil.copytree(source_skills, target_skills, dirs_exist_ok=True)
        print(f"✅ Copied skills directory (Stability Mode).")
    except Exception as e:
        print(f"❌ Failed to copy skills: {e}")

def sync_project_memory():
    """Mirror .agent/rules/constitution.md to .kittify/memory/constitution.md (if it exists)."""
    print("🧠 Syncing Project Memory...")
    source_constitution = AGENT_DIR / "rules" / "constitution.md"
    target_memory_dir = PROJECT_ROOT / ".kittify" / "memory"
    
    # Only sync if .kittify exists (Spec Kitty Project)
    if target_memory_dir.exists() and source_constitution.exists():
        target_file = target_memory_dir / "constitution.md"
        try:
            content = source_constitution.read_text(encoding="utf-8")
            target_file.write_text(content, encoding="utf-8")
            print(f"✅ Mirrored constitution to .kittify/memory/")
        except Exception as e:
            print(f"⚠️ Failed to mirror memory: {e}")

def sync_policies():
    """Mirror TOML policies from .agent/policies to USER_HOME/.gemini/policies."""
    print("🛡️ Syncing Policies...")
    source_policies = AGENT_DIR / "policies"
    # Gemini 3 Security: Policies must live in User Home, not project dir
    target_policies = Path.home() / ".gemini" / "policies"
    
    if not source_policies.exists():
        print("⚠️  No .agent/policies directory found. Creating empty one.")
        source_policies.mkdir(parents=True, exist_ok=True)
        
    # Clean target
    if target_policies.exists() or target_policies.is_symlink():
        try:
            if target_policies.is_symlink() or target_policies.is_file():
                target_policies.unlink()
            else:
                shutil.rmtree(target_policies, onerror=handle_remove_readonly)
        except Exception as e:
            print(f"⚠️  Could not clean .gemini/policies: {e}")

    # Copy (Robust fallback for Windows/WSL symlink issues)
    try:
        shutil.copytree(source_policies, target_policies, dirs_exist_ok=True)
        print(f"✅ Copied policies directory (Stability Mode).")
    except Exception as e:
        print(f"❌ Failed to copy policies: {e}")

def generate_command_wrappers():
    """Generate TOML wrappers for every workflow from .windsurf/workflows."""
    print("🚀 Generating Command Wrappers...")
    windsurf_dir = PROJECT_ROOT / ".windsurf"
    source_workflows = windsurf_dir / "workflows"
    target_commands = GEMINI_DIR / "commands"
    
    if not source_workflows.exists():
        print("⚠️  No .windsurf/workflows directory found. Skipping.")
        return

    count = 0
    # RECURSIVE: Find workflows in subfolders
    for workflow_file in source_workflows.rglob("*.md"):
        slug = workflow_file.stem
        
        try:
            workflow_content = workflow_file.read_text(encoding="utf-8")
            
            # Extract description from frontmatter if present
            description_match = None
            if workflow_content.startswith("---"):
                frontmatter_end = workflow_content.find("---", 3)
                if frontmatter_end != -1:
                    frontmatter = workflow_content[3:frontmatter_end]
                    for line in frontmatter.split("\n"):
                        if line.startswith("description:"):
                            description_match = line.split(":", 1)[1].strip().strip('"')
                            break
                    # Remove frontmatter from content
                    workflow_content = workflow_content[frontmatter_end + 3:].lstrip()
            
            description = description_match or f"Executes Antigravity Workflow: {slug}"
            # Escape double quotes for TOML string
            description = description.replace('"', '\\"')
            
            # Agent-specific replacements for Gemini
            workflow_content = workflow_content.replace('--actor "windsurf"', '--actor "gemini"')
            workflow_content = workflow_content.replace('$ARGUMENTS', '{{args}}')
            workflow_content = workflow_content.replace('(Missing script command for sh)', '(Missing script command for ps)')
            
            # Manually construct TOML with triple-quoted literal string for robustness (handles Windows paths)
            target_file = target_commands / f"{slug}.toml"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(f'description = "{description}"\n\n')
                f.write("prompt = '''\n")
                f.write(workflow_content)
                f.write("\n'''\n")
                
            print(f"✅ Generated {target_file.name}")
            count += 1
        except Exception as e:
            print(f"❌ Failed to generate wrapper for {slug}: {e}")
            
    print(f"✅ Generated {count} command wrappers.")

def sync_copilot_workflows():
    """Copy workflows from .windsurf/workflows to .github/prompts/ as .md files."""
    print("🤖 Syncing Workflows to GitHub Copilot...")
    windsurf_dir = PROJECT_ROOT / ".windsurf"
    source_workflows = windsurf_dir / "workflows"
    target_prompts = GITHUB_DIR / "prompts"
    
    if not source_workflows.exists():
        print("⚠️  No .windsurf/workflows directory found. Skipping.")
        return
    
    target_prompts.mkdir(parents=True, exist_ok=True)
    count = 0
    
    for workflow_file in source_workflows.rglob("*.md"):
        try:
            # Read workflow content
            workflow_content = workflow_file.read_text(encoding="utf-8")
            
            # Agent-specific replacements for Copilot
            workflow_content = workflow_content.replace('--actor "windsurf"', '--actor "copilot"')
            
            # Flatten: Save directly to .github/prompts/ (VS Code limit)
            target_file = target_prompts / f"{workflow_file.stem}.prompt.md"
            
            target_file.write_text(workflow_content, encoding="utf-8")
            
            print(f"✅ Copied {target_file.name}")
            count += 1
        except Exception as e:
            print(f"❌ Failed to copy {workflow_file.name} to Copilot prompts: {e}")
    
    print(f"✅ Synced {count} workflows to GitHub Copilot.")

def sync_custom_workflows_to_gemini():
    """Sync custom (non-spec-kitty) workflows from .agent/workflows to .gemini/commands as TOML."""
    print("🔧 Syncing Custom Workflows to Gemini...")
    source_workflows = AGENT_DIR / "workflows"
    target_commands = GEMINI_DIR / "commands"
    
    if not source_workflows.exists():
        print("⚠️  No .agent/workflows directory found. Skipping.")
        return
    
    count = 0
    
    # Recursively find all .md files in .agent/workflows and subdirectories
    for workflow_file in source_workflows.rglob("*.md"):
        # Filter: Skip spec-kitty workflows
        if "spec-kitty" in workflow_file.stem.lower():
            continue
        
        try:
            workflow_content = workflow_file.read_text(encoding="utf-8")
            
            # Extract description from frontmatter if present
            description_match = None
            if workflow_content.startswith("---"):
                frontmatter_end = workflow_content.find("---", 3)
                if frontmatter_end != -1:
                    frontmatter = workflow_content[3:frontmatter_end]
                    for line in frontmatter.split("\n"):
                        if line.startswith("description:"):
                            description_match = line.split(":", 1)[1].strip().strip('"')
                            break
                    # Remove frontmatter from content
                    workflow_content = workflow_content[frontmatter_end + 3:].lstrip()
            
            description = description_match or f"Executes Custom Workflow: {workflow_file.stem}"
            # Escape double quotes for TOML string
            description = description.replace('"', '\\"')
            
            # Agent-specific replacements for Gemini
            workflow_content = workflow_content.replace('--actor "windsurf"', '--actor "gemini"')
            workflow_content = workflow_content.replace('--actor "antigravity"', '--actor "gemini"')
            workflow_content = workflow_content.replace('$ARGUMENTS', '{{args}}')
            workflow_content = workflow_content.replace('(Missing script command for sh)', '(Missing script command for ps)')
            
            # Preserve subdirectory structure
            rel_path = workflow_file.relative_to(source_workflows)
            target_file = target_commands / rel_path.parent / f"{workflow_file.stem}.toml"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write TOML with triple-quoted literal string
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(f'description = "{description}"\n\n')
                f.write("prompt = '''\n")
                f.write(workflow_content)
                f.write("\n'''\n")
            
            print(f"✅ Generated {rel_path.parent / target_file.name}")
            count += 1
        except Exception as e:
            print(f"❌ Failed to generate wrapper for {workflow_file.name}: {e}")
    
    print(f"✅ Synced {count} custom workflows to Gemini.")

def sync_custom_workflows_to_copilot():
    """Sync custom (non-spec-kitty) workflows from .agent/workflows to .github/prompts as .md files."""
    print("🤖 Syncing Custom Workflows to GitHub Copilot...")
    source_workflows = AGENT_DIR / "workflows"
    target_prompts = GITHUB_DIR / "prompts"
    
    if not source_workflows.exists():
        print("⚠️  No .agent/workflows directory found. Skipping.")
        return
    
    count = 0
    
    # Recursively find all .md files in .agent/workflows and subdirectories
    for workflow_file in source_workflows.rglob("*.md"):
        # Filter: Skip spec-kitty workflows
        if "spec-kitty" in workflow_file.stem.lower():
            continue
        
        try:
            workflow_content = workflow_file.read_text(encoding="utf-8")
            
            # Agent-specific replacements for Copilot
            workflow_content = workflow_content.replace('--actor "windsurf"', '--actor "copilot"')
            workflow_content = workflow_content.replace('--actor "antigravity"', '--actor "copilot"')
            
            # Flatten: Save directly to .github/prompts/ (VS Code limit)
            target_file = target_prompts / f"{workflow_file.stem}.prompt.md"
            
            target_file.write_text(workflow_content, encoding="utf-8")
            
            print(f"✅ Copied {target_file.name}")
            count += 1
        except Exception as e:
            print(f"❌ Failed to copy {workflow_file.name} to Copilot prompts: {e}")
    
    print(f"✅ Synced {count} custom workflows to GitHub Copilot.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Dual-Tri Bridge Sync Engine")
    parser.add_argument("--inbound", action="store_true", help="Run Phase 1: Upstream (.windsurf) -> Core (.agent)")
    parser.add_argument("--outbound", action="store_true", help="Run Phase 2: Core (.agent) -> Downstream (.gemini/.github)")
    args = parser.parse_args()

    # Default: Run BOTH if no flags specified
    run_inbound = args.inbound
    run_outbound = args.outbound
    if not run_inbound and not run_outbound:
        run_inbound = True
        run_outbound = True

    if not AGENT_DIR.exists():
        print(f"❌ Critical: .agent directory not found at {AGENT_DIR}")
        return
        
    setup_directories()

    # --- PHASE 2: STANDARD BRIDGE (Layer 1) ---
    if run_inbound:
        print("\n🔵 [PHASE 2] STANDARD BRIDGE (Layer 1): Upstream (.windsurf) -> All Agents")
        try:
            # 1. Ingest Standard Kit to Core
            sync_from_upstream()
            
            # 2. Project Standard Kit to Gemini/Copilot (Immediate Availability)
            print("   >> Propagating Standard Kit to Downstream Agents...")
            generate_command_wrappers()  # Gemini TOML
            sync_copilot_workflows()      # GitHub Copilot .md
            
        except Exception as e:
            print(f"❌ Error in Phase 2: {e}")

    # --- PHASE 3: CUSTOM BRIDGE (Layer 2) ---
    if run_outbound:
        print("\n🟣 [PHASE 3] CUSTOM BRIDGE (Layer 2): Project Custom Rules -> Downstream")
        # In this implementation, 'sync_to_downstream' handles both Standard + Custom
        # running it again here ensures any MANUALLY added custom rules in .agent are synced.
        try:
             # sync_instructions()
             # sync_skills()
             # sync_policies()
             sync_custom_workflows_to_gemini()
             sync_custom_workflows_to_copilot()
        except Exception as e:
            print(f"❌ Error in Phase 3: {e}")




    print("\n🎉 Bridge Sync Complete.")

if __name__ == "__main__":
    main()

