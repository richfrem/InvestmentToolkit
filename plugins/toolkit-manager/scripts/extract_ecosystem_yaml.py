#!/usr/bin/env python3
"""
=============================================================================
File: extract_ecosystem_yaml.py
Purpose: Extracts YAML frontmatter 'name' and 'description' from markdown 
         files across the ecosystem (plugins, skills, agents) and generates 
         a summary markdown file.
=============================================================================
"""

import os
import glob
import re
from typing import Dict

# Extracts the YAML frontmatter name and description from a given file path.
def get_fm(filepath: str) -> Dict[str, str]:
    """
    Extracts YAML frontmatter 'name' and 'description' from a markdown file.
    
    Args:
        filepath: The absolute or relative path to the markdown file.
        
    Returns:
        A dictionary containing 'name' and 'description' keys. Returns an 
        empty dict if parsing fails or no frontmatter is found.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    name_match = re.search(r'^name:\s*(.+)$', parts[1], re.M)
                    desc_match = re.search(r'^description:\s*(.+)$', parts[1], re.M)
                    return {
                        'name': name_match.group(1).strip() if name_match else '',
                        'description': desc_match.group(1).strip() if desc_match else ''
                    }
    except Exception:
        pass
    return {}

# Main execution function for extracting ecosystem yaml frontmatter.
def main() -> None:
    """
    Orchestrates the discovery of plugins, skills, and agents across the 
    repository, extracts their YAML frontmatter, and writes a summary report.
    """
    # repo_root is three levels up from plugins/toolkit-manager/scripts/
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    out = []
    out.append("# Ecosystem YAML Summary\n")
    
    out.append("## PLUGINS")
    plugins_dir = os.path.join(repo_root, 'plugins')
    if os.path.isdir(plugins_dir):
        for d in sorted(os.listdir(plugins_dir)):
            path = os.path.join(plugins_dir, d)
            if os.path.isdir(path):
                out.append(f"- **{d}**")

    out.append("\n## SKILLS")
    skills_glob = os.path.join(repo_root, '.agents/skills/*/SKILL.md')
    for p in sorted(glob.glob(skills_glob)):
        fm = get_fm(p)
        name = fm.get('name')
        desc = fm.get('description', '')
        if desc:
            desc = desc[:150] + ('...' if len(desc) > 150 else '')
        out.append(f"- **{os.path.basename(os.path.dirname(p))}**: {name} | {desc}")

    out.append("\n## AGENTS")
    agents_glob = os.path.join(repo_root, '.agents/agents/*.md')
    for p in sorted(glob.glob(agents_glob)):
        fm = get_fm(p)
        name = fm.get('name')
        desc = fm.get('description', '')
        if desc:
            desc = desc[:150] + ('...' if len(desc) > 150 else '')
        out.append(f"- **{os.path.basename(p)}**: {name} | {desc}")

    output_path = os.path.join(repo_root, 'ecosystem_yaml_summary.md')
    with open(output_path, 'w') as f:
        f.write('\n'.join(out))
    
    print(f"Extraction complete. Output written to {output_path}")

if __name__ == '__main__':
    main()
