#!/usr/bin/env python3
"""
manage_servers.py - Smart server management for Spec Kitty worktrees.

Usage:
    python3 tools/manage_servers.py [action] [target] [worktree_path]

Actions:
    start   - Start servers (default)
    stop    - Stop servers running on ports 3001 and 5173
    restart - Stop then start

Targets:
    all      - Both backend and frontend (default)
    backend  - Only the Node.js backend (port 3001)
    frontend - Only the Vite frontend (port 5173)

Worktree Path:
    Optional. Defaults to current directory.
    If provided, script changes to that directory before starting servers.

Examples:
    python3 tools/manage_servers.py start all .worktrees/WP05
    python3 tools/manage_servers.py stop
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path

# Configuration
PORTS = {
    'backend': 3001,
    'frontend': 5173
}

def find_pid_by_port(port):
    """Find PID using lsof."""
    try:
        output = subprocess.check_output(f"lsof -ti:{port}", shell=True).decode().strip()
        if output:
            return [int(pid) for pid in output.split('\n')]
    except subprocess.CalledProcessError:
        return []
    return []

def stop_servers(target='all'):
    """Stop servers based on target."""
    print(f"🛑 Stopping {target} servers...")
    
    targets = ['backend', 'frontend'] if target == 'all' else [target]
    
    for t in targets:
        port = PORTS.get(t)
        if not port: continue
        
        pids = find_pid_by_port(port)
        if pids:
            print(f"   Killing {t} on port {port} (PIDs: {pids})")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        else:
            print(f"   No {t} server found on port {port}")

def start_servers(target='all', worktree_path='.'):
    """Start servers in background."""
    base_path = Path(worktree_path).resolve()
    print(f"🚀 Starting {target} servers in {base_path}...")
    
    # Check project structure
    screener_path = base_path / 'tools' / 'investment-screener'
    if not screener_path.exists():
        print(f"❌ Error: tools/investment-screener not found in {base_path}")
        return

    targets = ['backend', 'frontend'] if target == 'all' else [target]
    
    for t in targets:
        # Check if port is free
        if find_pid_by_port(PORTS[t]):
            print(f"⚠️  Warning: Port {PORTS[t]} is already in use. Killing old process...")
            stop_servers(t)
            time.sleep(1)

        server_dir = screener_path / t
        if not server_dir.exists():
             print(f"❌ Error: Directory {server_dir} does not exist")
             continue

        print(f"   Starting {t} in {server_dir}...")
        
        cmd = "npm run dev"  # Both frontend and backend use npm run dev
        
        # Use simple Popen but direct output to log files or /dev/null to avoid cluttering current shell
        # We invoke via shell/nohup to let them persist if this script exits? 
        # Actually standard practice for dev tools is usually new terminal tabs or backgrounding.
        # Here we'll background them.
        
        log_file = open(base_path / f"{t}.log", "w")
        subprocess.Popen(
            cmd, 
            cwd=str(server_dir), 
            shell=True,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
        print(f"   ✅ {t} started (logs: {t}.log)")

def main():
    if len(sys.argv) < 2:
        action = 'start'
    else:
        action = sys.argv[1]

    if len(sys.argv) < 3:
        target = 'all'
    else:
        target = sys.argv[2]
        
    if len(sys.argv) < 4:
        worktree = '.'
    else:
        worktree = sys.argv[3]

    if action == 'stop':
        stop_servers(target)
    elif action == 'restart':
        stop_servers(target)
        time.sleep(1)
        start_servers(target, worktree)
    elif action == 'start':
        start_servers(target, worktree)
    else:
        print("Usage: python3 tools/manage_servers.py [start|stop|restart] [all|backend|frontend] [path]")

if __name__ == "__main__":
    main()
