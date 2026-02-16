import json
import os
from pathlib import Path

# Known mappings from MIGRATION_GUIDE.md and analysis
KNOWN_MAPPINGS = {
    # Vector DB
    "tools/codify/vector/ingest.py": "plugins/vector-db/scripts/ingest.py",
    "tools/retrieve/vector/query.py": "plugins/vector-db/scripts/query.py",
    "tools/curate/vector/cleanup.py": "plugins/vector-db/scripts/cleanup.py",
    "tools/codify/vector/ingest_code_shim.py": "plugins/vector-db/scripts/ingest_code_shim.py",

    # RLM
    "tools/codify/rlm/distiller.py": "plugins/rlm-factory/scripts/distiller.py",
    "tools/retrieve/rlm/query_cache.py": "plugins/rlm-factory/scripts/query_cache.py",
    "tools/retrieve/rlm/inventory.py": "plugins/rlm-factory/scripts/inventory.py", # Moved to rlm-factory based on ls output
    
    # Tool Inventory
    "tools/curate/inventories/manage_tool_inventory.py": "plugins/tool-inventory/scripts/manage_tool_inventory.py",
    "tools/codify/rlm/rlm_config.py": "plugins/tool-inventory/scripts/rlm_config.py", # Reasonable guess
    "tools/curate/rlm/cleanup_cache.py": "plugins/rlm-factory/scripts/cleanup_cache.py", # Corrected destination based on ls output

    # Link Checker
    "tools/codify/documentation/check_broken_paths.py": "plugins/link-checker/scripts/check_broken_paths.py",
    "tools/codify/documentation/map_repository_files.py": "plugins/link-checker/scripts/map_repository_files.py",
    "tools/curate/link-checker/check_broken_paths.py": "plugins/link-checker/scripts/check_broken_paths.py", # Duplicate
    "tools/curate/link-checker/map_repository_files.py": "plugins/link-checker/scripts/map_repository_files.py", # Duplicate
    "tools/curate/link-checker/smart_fix_links.py": "plugins/link-checker/scripts/smart_fix_links.py",

    # Context Bundler
    "tools/retrieve/bundler/bundle.py": "plugins/context-bundler/scripts/bundle.py",
    "tools/retrieve/bundler/manifest_manager.py": "plugins/context-bundler/scripts/manifest_manager.py",
    "tools/investigate/utils/path_resolver.py": "plugins/context-bundler/scripts/path_resolver.py",
    "tools/utils/path_resolver.py": "plugins/context-bundler/scripts/path_resolver.py",

    # Spec Kitty / Bridge
    "tools/bridge/speckit_system_bridge.py": "plugins/spec-kitty/scripts/speckit_system_bridge.py",
    "tools/bridge/sync_workflows.py": "plugins/spec-kitty/scripts/sync_workflows.py",
    "tools/bridge/sync_rules.py": "plugins/spec-kitty/scripts/sync_rules.py",
    "tools/bridge/sync_skills.py": "plugins/spec-kitty/scripts/sync_skills.py",
    "tools/bridge/verify_bridge_integrity.py": "plugins/spec-kitty/scripts/verify_bridge_integrity.py",

    # Mermaid
    "tools/codify/diagrams/export_mmd_to_image.py": "plugins/mermaid-export/scripts/export_mmd_to_image.py",

    # Agent Orchestrator
    "plugins/spec-kitty/scripts/agent_orchestrator.py": "plugins/agent-orchestrator/scripts/agent_orchestrator.py", # inferred
    
    # ADR Manager
    "tools/investigate/utils/next_number.py": "plugins/adr-manager/scripts/next_number.py",
    
    # Code Snapshot (New?)
    "tools/snapshot_utils.py": "plugins/code-snapshot/scripts/snapshot_utils.py", # Guess
}

# Paths to explicitly exclude from migration (they will be deleted later or handled manually)
EXCLUDE_PREFIXES = [
    "tools/standalone/",
    "tools/investment-screener/",  # Treat as separate app
]

def find_files(root_dir, skip_dirs=None, extensions=None):
    if skip_dirs is None:
        skip_dirs = []
    file_list = []
    for root, dirs, files in os.walk(root_dir):
        # Modify dirs in-place to skip
        dirs[:] = [d for d in dirs if d not in skip_dirs and d != '__pycache__']
        for file in files:
            if extensions and not any(file.endswith(ext) for ext in extensions):
                continue
            file_list.append(os.path.join(root, file))
    return file_list

def map_workflows():
    """Map .agent/workflows/*.md to plugins/*/commands/*.md"""
    workflow_files = find_files(".agent/workflows", extensions=[".md"])
    plugin_commands = find_files("plugins", extensions=[".md"])
    
    # Filter only commands/ directories in plugins
    plugin_commands = [p for p in plugin_commands if "/commands/" in p]
    
    mappings = {}
    
    # Create target map: command_name.md -> full_path
    target_map = {}
    for p in plugin_commands:
        name = os.path.basename(p)
        target_map[name] = p
        
    for wf in workflow_files:
        name = os.path.basename(wf)
        # Try exact match
        if name in target_map:
            mappings[wf] = target_map[name]
        else:
            # Try mapping common prefixes/names
            # e.g. manage-tool-inventory.md vs manage.md in tool-inventory plugin
            pass
            
    return mappings

def map_skills():
    """Map .agent/skills/<name> to plugins/*/skills/<name>"""
    # This is trickier because skills are directories.
    # We'll list top-level directories in .agent/skills
    skills_root = ".agent/skills"
    if not os.path.exists(skills_root):
        return {}
        
    agent_skills = [d for d in os.listdir(skills_root) if os.path.isdir(os.path.join(skills_root, d))]
    
    # Find skill directories in plugins
    # plugins/<plugin>/skills/<skill-name>
    plugin_skills = []
    for root, dirs, files in os.walk("plugins"):
        if "skills" in dirs:
            skills_dir = os.path.join(root, "skills")
            for sk in os.listdir(skills_dir):
                if os.path.isdir(os.path.join(skills_dir, sk)):
                    plugin_skills.append(os.path.join(skills_dir, sk))

    mappings = {}
    
    for askill in agent_skills:
        askill_path = os.path.join(skills_root, askill)
        
        # Try to find matching skill folder name
        # Note: plugin skill names might differ (e.g. dependency-management vs dependency-agent)
        
        # 1. Exact match of directory name
        match = next((p for p in plugin_skills if os.path.basename(p) == askill), None)
        
        # 2. Heuristic: Plugin name matches skill name
        if not match:
             # e.g. .agent/skills/dependency-management -> plugins/dependency-management/skills/*
             # check if any plugin has a name matching the skill
             for p_skill_path in plugin_skills:
                 # p_skill_path like plugins/dependency-management/skills/dependency-agent
                 parts = p_skill_path.split(os.sep)
                 if len(parts) >= 2:
                     plugin_name = parts[1] # plugins/<plugin_name>/...
                     if plugin_name == askill:
                         match = p_skill_path
                         break

        if match:
             # Map the directory itself
             mappings[askill_path] = match
             
             # Also map all files inside recursively
             for root, _, files in os.walk(askill_path):
                 for f in files:
                     src_file = os.path.join(root, f)
                     rel_from_skill = os.path.relpath(src_file, askill_path)
                     dest_file = os.path.join(match, rel_from_skill)
                     mappings[src_file] = dest_file

    return mappings

def generate_inventory():
    tools_files = find_files("tools", skip_dirs=[".git", "node_modules", "venv", ".venv"], extensions=[".py"])
    plugins_files = find_files("plugins", skip_dirs=[".git", "node_modules", "venv", ".venv"], extensions=[".py"])
    
    inventory = {}
    
    # --- TOOLS MAPPING ---
    # Create potential targets map: filename -> full_path
    plugin_targets = {}
    for p in plugins_files:
        filename = os.path.basename(p)
        if filename not in plugin_targets:
            plugin_targets[filename] = []
        plugin_targets[filename].append(p)

    tools_files.sort()
    
    for tool_path in tools_files:
        # Normalize path
        rel_path = os.path.relpath(tool_path, ".")
        
        # Skip cli.py and orchestrator/workflow_manager.py as they persist
        if rel_path == "tools/cli.py":
            continue
        if rel_path == "plugins/spec-kitty/scripts/workflow_manager.py":
            continue

        # Skip explicit exclusions
        if any(rel_path.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
            continue

        new_path = None
        status = "pending"
        
        # Check known mappings first
        if rel_path in KNOWN_MAPPINGS:
            new_path = KNOWN_MAPPINGS[rel_path]
        else:
            # Try to match by filename
            filename = os.path.basename(rel_path)
            if filename in plugin_targets:
                 candidates = plugin_targets[filename]
                 if len(candidates) == 1:
                     new_path = candidates[0]
                 else:
                     # Heuristic: Prefer path with similar parent dir name
                     best_match = None
                     tool_parts = rel_path.split(os.sep)
                     for cand in candidates:
                         cand_parts = cand.split(os.sep)
                         if set(tool_parts) & set(cand_parts):
                             best_match = cand
                             break
                     new_path = best_match if best_match else candidates[0]
            
        if new_path:
             if not os.path.exists(new_path):
                 status = "target_missing"
        else:
            status = "unmapped"
        
        inventory[rel_path] = {
            "new_path": new_path,
            "status": status
        }

    # --- WORKFLOWS MAPPING ---
    wf_mappings = map_workflows()
    for src, dst in wf_mappings.items():
        rel_src = os.path.relpath(src, ".")
        rel_dst = os.path.relpath(dst, ".")
        inventory[rel_src] = {
            "new_path": rel_dst,
            "status": "pending"
        }
        
    # --- SKILLS MAPPING ---
    skill_mappings = map_skills()
    for src, dst in skill_mappings.items():
        rel_src = os.path.relpath(src, ".")
        rel_dst = os.path.relpath(dst, ".")
        inventory[rel_src] = {
            "new_path": rel_dst,
            "status": "pending"
        }

    with open("migration_inventory.json", "w") as f:
        json.dump(inventory, f, indent=2)
    
    print(f"Generated inventory for {len(inventory)} items.")

    
    # Print unmapped items for review
    unmapped = [k for k, v in inventory.items() if v['status'] == 'unmapped']
    if unmapped:
        print("\nUnmapped items:")
        for item in unmapped:
            print(f"  {item}")

if __name__ == "__main__":
    generate_inventory()
