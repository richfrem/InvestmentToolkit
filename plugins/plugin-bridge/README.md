# Plugin Bridge

**Universal Plugin Installer**

The **Plugin Bridge** allows you to write Agent Plugins *once* in the standard portable format (`.claude-plugin`, `commands/`, `skills/`) and deploy them automatically to:
- **Antigravity** (Project Sanctuary agents)
- **GitHub Copilot** (VS Code chat)
- **Gemini** (Windsurf / Codespaces)

## Features
- **Auto-Detection**: Scans your repo for `.agent`, `.github`, or `.gemini` folders.
- **Workflow Mapping**: Converts Markdown commands to `.prompt.md` (GitHub) or `.toml` (Gemini).
- **Skill Deployment**: Copies skills to the correct agent locations.
- **Resource Syncing**: Automatically deploys `resources/` (manifests, prompts) to the `tools/` mirror for path parity.

## Customization & Resources
Many plugins (like `rlm-factory`) use a `resources/` directory for configuration. If your plugin requires custom manifests or templates:
1.  **Edit Local JSONs**: Update the files in `plugins/your-plugin/resources/`.
2.  **Re-Run Bridge**: Execute the installer to synchronize these changes to the `tools/` fallback directory.
Run the install command:
```bash
python3 plugins/plugin-bridge/scripts/bridge_installer.py --plugin plugins/my-plugin
```
