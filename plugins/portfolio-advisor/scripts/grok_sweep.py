#!/usr/bin/env python3
"""
grok_sweep.py (Python Service)
===============================

Purpose:
    Posts a pre-generated prompt to grok.com via Chrome DevTools Protocol and captures the response.
    Used by the x-news-sweep skill to automate the full Grok sweep without manual copy-paste.

Layer: Backend / Python Services / Browser Automation

Requirements:
    - Chrome launched with --remote-debugging-port=9223 --user-data-dir=/tmp/chrome-bu-profile
    - browser-harness cloned at $BROWSER_HARNESS_DIR (default: ~/projects/browser-harness)
    - First-time: authorize grok.com via X OAuth in that Chrome window

Usage Examples:
    python3 grok_sweep.py
    python3 grok_sweep.py --prompt /tmp/grok_sweep_prompt.md --output /tmp/grok_sweep_response.md
    python3 grok_sweep.py --cdp-port 9223

Key Functions:
    - get_cdp_ws()      - Resolves the Chrome DevTools WebSocket URL from the debug port
    - run_sweep()       - Posts the prompt via browser-harness and extracts the response
    - extract_response() - Strips sidebar/input from document.body.innerText using known markers
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_TEMP_DIR = os.path.join(_REPO_ROOT, "temp")
os.makedirs(_TEMP_DIR, exist_ok=True)

DEFAULT_PROMPT_FILE = os.path.join(_TEMP_DIR, "grok_sweep_prompt.md")
DEFAULT_OUTPUT_FILE = os.path.join(_TEMP_DIR, "grok_sweep_response.md")
DEFAULT_CDP_PORT = 9223

# The automation code piped into browser-harness stdin
HARNESS_SCRIPT = '''
import time, json

with open({prompt_file!r}) as f:
    prompt = f.read()

cdp("Emulation.setFocusEmulationEnabled", enabled=True)

new_tab("https://grok.com/")
wait_for_load()
time.sleep(3)

click_at_xy(660, 266)
time.sleep(0.5)

tag = js("document.activeElement.tagName")
assert tag == "DIV", f"focus failed — activeElement is {{tag}}, expected DIV"

prompt_escaped = json.dumps(prompt)
js(f"document.execCommand('insertText', false, {{prompt_escaped}})")
time.sleep(0.5)

chars = js("document.activeElement ? document.activeElement.innerText.length : 0")
assert chars > 100, f"text did not land: {{chars}} chars"

press_key("Enter")
time.sleep(5)

# Wait for Stop button to disappear (response complete)
for i in range(60):
    time.sleep(3)
    has_stop = js("""
        var btns = document.querySelectorAll('button');
        Array.from(btns).some(function(b){{ return b.getAttribute('aria-label') === 'Stop'; }});
    """)
    if not has_stop and i > 3:
        break

time.sleep(2)

# Scroll internal container to top so full response is captured
js("""
var container = Array.from(document.querySelectorAll('*'))
    .filter(function(el){{ return el.scrollHeight > el.clientHeight + 100 && el.clientHeight > 200; }})
    .sort(function(a,b){{ return b.scrollHeight - a.scrollHeight; }})[0];
if(container) container.scrollTop = 0;
""")
time.sleep(0.5)

# Extract via innerText — clipboard API is blocked in CDP contexts
full = js("document.body.innerText")
marker = "Thought for"
idx = full.find(marker)
response = full[idx:] if idx >= 0 else full
cutoff = response.find("\\nAsk anything")
if cutoff > 0:
    response = response[:cutoff]

with open({output_file!r}, "w") as f:
    f.write(response)

print(f"response captured: {{len(response)}} chars")
'''


def get_cdp_ws(port: int) -> str:
    url = f"http://127.0.0.1:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.load(resp)
            ws = data.get("webSocketDebuggerUrl")
            if not ws:
                raise RuntimeError(f"no webSocketDebuggerUrl in response: {data}")
            return ws
    except Exception as e:
        raise RuntimeError(
            f"Chrome not reachable on port {port}. "
            f"Launch it with: \"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome\" "
            f"--remote-debugging-port={port} --user-data-dir=/tmp/chrome-bu-profile &"
        ) from e


def run_sweep(prompt_file: str, output_file: str, cdp_port: int) -> str:
    harness_dir = os.path.expanduser(
        os.environ.get("BROWSER_HARNESS_DIR", "~/projects/browser-harness")
    )

    ws_url = get_cdp_ws(cdp_port)
    script = HARNESS_SCRIPT.format(prompt_file=prompt_file, output_file=output_file)

    env = os.environ.copy()
    env["BU_CDP_WS"] = ws_url

    result = subprocess.run(
        ["uv", "run", "--project", harness_dir, "browser-harness"],
        input=script,
        text=True,
        capture_output=True,
        env=env,
    )

    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"browser-harness exited {result.returncode}")

    print(result.stdout.strip())
    return output_file


def extract_response(output_file: str) -> str:
    with open(output_file) as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(description="Post sweep prompt to grok.com and capture response")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT_FILE, help="Path to the generated sweep prompt")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE, help="Path to write the captured response")
    parser.add_argument("--cdp-port", type=int, default=DEFAULT_CDP_PORT, help="Chrome remote debugging port")
    args = parser.parse_args()

    if not os.path.exists(args.prompt):
        print(f"Error: prompt file not found: {args.prompt}", file=sys.stderr)
        print(f"Run first: python3 generate_grok_prompt.py --output {DEFAULT_PROMPT_FILE}", file=sys.stderr)
        sys.exit(1)

    print(f"CDP port:    {args.cdp_port}")
    print(f"Prompt:      {args.prompt} ({os.path.getsize(args.prompt)} bytes)")
    print(f"Output:      {args.output}")

    run_sweep(args.prompt, args.output, args.cdp_port)

    response = extract_response(args.output)
    print(f"\nResponse written: {len(response)} chars → {args.output}")


if __name__ == "__main__":
    main()
