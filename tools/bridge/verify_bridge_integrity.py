#!/usr/bin/env python3
"""
verify_bridge_integrity.py
=====================================
Purpose:
    Audits the "Dual Tri Bridge" synchronization.
    Verifies that every artifact in .agent/ is correctly represented in:
    1. .gemini/ (CLI)
    2. .github/ (Copilot)

Usage:
    python tools/bridge/verify_bridge_integrity.py
"""
import sys
import os
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_DIR = PROJECT_ROOT / ".agent"
GEMINI_DIR = PROJECT_ROOT / ".gemini"
GITHUB_DIR = PROJECT_ROOT / ".github"

def check_rules():
    print("\n🔍 Checking Rules...")
    source = AGENT_DIR / "rules"
    target_gemini = GEMINI_DIR / "rules"
    target_copilot = GITHUB_DIR / "copilot-instructions.md"
    
    missing = []
    
    # Check Gemini Mirror (Content Injection Check)
    # Rules are now injected into GEMINI.md, not copied to .gemini/rules
    gemini_md = PROJECT_ROOT / "GEMINI.md"
    if gemini_md.exists():
        content = gemini_md.read_text(encoding="utf-8")
        for rule in source.rglob("*.md"):
            # We look for the filename or title in GEMINI.md
            # The bridge injects them as "## {rule.stem}"
            if f"## {rule.stem}" not in content and rule.stem != "constitution": # Constitution has special header
                 missing.append(f"Gemini: Rule {rule.stem} not injected in GEMINI.md")
    else:
        missing.append("Gemini: GEMINI.md missing")
            
    # Check Copilot Index (Simple text check)
    if target_copilot.exists():
        content = target_copilot.read_text(encoding="utf-8")
        for rule in source.rglob("*.md"):
            if f"Rule: {rule.stem}" not in content:
                 missing.append(f"Copilot: {rule.name} not in instructions")
    else:
        missing.append("Copilot: copilot-instructions.md missing")
        
    if missing:
        for m in missing: print(f"  ❌ Missing: {m}")
        return False
    print("  ✅ All Rules Verified.")
    return True

def check_workflows():
    print("\n🔍 Checking Workflows...")
    source = AGENT_DIR / "workflows"
    target_gemini = GEMINI_DIR / "commands"
    target_copilot = GITHUB_DIR / "prompts"
    
    missing = []
    
    # Use rglob to find all workflows
    for wf in source.rglob("*.md"):
        # Check Gemini TOML
        # Check Gemini TOML
        # The bridge preserves the directory structure, so we must check relative paths
        rel_path = wf.relative_to(source)
        toml_rel_path = rel_path.with_suffix(".toml")
        
        if not (target_gemini / toml_rel_path).exists():
            # Fallback: Check strictly by name in case of flat-mapping (for standard kit)
            # Standard kit from .windsurf is flat-mapped to commands/
            if not (target_gemini / f"{wf.stem}.toml").exists():
                 missing.append(f"Gemini: {toml_rel_path} (Source: {wf.name})")
            
        # Check Copilot Prompt
        prompt_name = f"{wf.stem}.prompt.md"
        if not (target_copilot / prompt_name).exists():
            missing.append(f"Copilot: {prompt_name}")
            
    if missing:
        for m in missing: print(f"  ❌ Missing: {m}")
        return False
    print("  ✅ All Workflows Verified.")
    return True

def check_skills():
    print("\n🔍 Checking Skills...")
    source = AGENT_DIR / "skills"
    target_gemini = GEMINI_DIR / "skills"
    
    missing = []
    
    if source.exists():
        for skill in source.iterdir():
            if skill.is_dir():
                if not (target_gemini / skill.name).exists():
                    missing.append(f"Gemini: skills/{skill.name}")
    
    if missing:
        for m in missing: print(f"  ❌ Missing: {m}")
        print("  ⚠️  Skills are NOT fully synced.")
        return False
        
    print("  ✅ All Skills Verified.")
    return True

def main():
    print("=========================================")
    print("   Dual Tri Bridge Integrity Check")
    print("=========================================")
    
    results = [
        check_rules(),
        check_workflows(),
        check_skills()
    ]
    
    if all(results):
        print("\n🎉 INTEGRITY VERIFIED: System is practically perfect.")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED: Sync required.")
        sys.exit(1)

if __name__ == "__main__":
    main()
