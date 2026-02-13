#!/usr/bin/env python3
"""
manage_servers.py
=====================================

Purpose:
    Provides centralized management for the InvestmentToolkit development servers.
    Handles starting, stopping, and restarting the Node.js backend and Vite frontend.
    Also provides a CLI interface for Questrade token seeding and status checks.

Layer: Tools / Infrastructure

Usage Examples:
    python tools/manage_servers.py start all
    python tools/manage_servers.py stop backend
    python tools/manage_servers.py restart frontend --path .worktrees/WP05
    python tools/manage_servers.py seed --token <REFRESH_TOKEN>
    python tools/manage_servers.py status

CLI Arguments:
    action        : Command to execute (start, stop, restart, seed, status)
    target        : Server to target (all, backend, frontend) - Optional for start/stop/restart
    --path        : Optional worktree path (default: current directory)
    --token       : Questrade refresh token (required for 'seed')

Key Functions:
    - start_servers()  : Backgrounds dev servers and directs output to logs.
    - stop_servers()   : Safely terminates processes running on toolkit ports.
    - seed_token()     : Seeds a Questrade refresh token via the backend API.
    - check_status()   : Verifies server health and portfolio sync status.

Related:
    - cli.py
    - investment-screener/
"""

import sys
import os
import subprocess
import time
import signal
import argparse
import json
from pathlib import Path
from typing import List, Optional

# Configuration - Toolkit Ports
PORTS = {
    'backend': 3001,
    'frontend': 5173
}


def find_pids(port: int) -> List[int]:
    """
    Identifies process IDs associated with a specific network port.

    Args:
        port: The network port to check.

    Returns:
        List of integer PIDs.
    """
    try:
        # Using lsof -ti for silent, ID-only output
        output = subprocess.check_output(f"lsof -ti:{port}", shell=True).decode().strip()
        if output:
            return [int(pid) for pid in output.split('\n')]
    except subprocess.CalledProcessError:
        return []
    return []


def stop_servers(target: str = 'all') -> None:
    """
    Terminates running dev servers based on the target category.

    Args:
        target: 'all', 'backend', or 'frontend'.
    """
    print(f"🛑 Stopping {target} servers...")
    
    targets = ['backend', 'frontend'] if target == 'all' else [target]
    
    # 1. Port-based termination (Direct)
    for t in targets:
        port = PORTS.get(t)
        if not port:
            continue
        
        pids = find_pids(port)
        if pids:
            print(f"   Terminating {t} on port {port} (PIDs: {pids})")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        else:
            print(f"   No {t} server detected on port {port}")

    # 2. Path-based "Ghost Hunting" (Robust)
    # Check for any lingering node processes running from this workspace's toolkit folders
    try:
        # We look for processes containing 'investment-screener' in their path
        search_cmd = "ps aux | grep 'investment-screener' | grep -E 'node|vite|ts-node-dev' | grep -v grep | awk '{print $2}'"
        ghost_pids = subprocess.check_output(search_cmd, shell=True).decode().strip().split('\n')
        ghost_pids = [int(p) for p in ghost_pids if p]
        
        if ghost_pids:
            print(f"   👻 Found {len(ghost_pids)} ghost processes haunting the toolkit. Exorcising...")
            for pid in ghost_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
    except subprocess.CalledProcessError:
        pass # No ghosts found


def start_servers(target: str = 'all', worktree_path: str = '.') -> None:
    """
    Starts the development servers in the background.

    Args:
        target: 'all', 'backend', or 'frontend'.
        worktree_path: The directory containing the screener source.
    """
    base_path = Path(worktree_path).resolve()
    print(f"🚀 Starting {target} servers in {base_path}...")
    
    # Verify toolkit source exists
    screener_path = base_path / 'tools' / 'investment-screener'
    if not screener_path.exists():
        print(f"❌ Error: 'tools/investment-screener' not found in {base_path}")
        return

    targets = ['backend', 'frontend'] if target == 'all' else [target]
    
    for t in targets:
        # Port conflict resolution
        port = PORTS[t]
        if find_pids(port):
            print(f"⚠️  Port {port} in use. Clearing old process...")
            stop_servers(t)
            time.sleep(1)

        server_dir = screener_path / t
        if not server_dir.exists():
             print(f"❌ Error: Module directory {server_dir} missing.")
             continue

        print(f"   Launching {t}...")
        
        # Standard toolkit dev command
        cmd = "npm run dev"
        log_path = base_path / f"{t}_server.log"
        
        with open(log_path, "w") as log_file:
            subprocess.Popen(
                cmd, 
                cwd=str(server_dir), 
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True # Detach from parent
            )
        print(f"   ✅ {t} active. Logs: {log_path.name}")

    if target in ['all', 'frontend']:
        print(f"\n✨ Toolkit Ready! Access UI at: http://localhost:5173")
        print(f"👉 To link Questrade: Open UI -> Sidebar -> 'Link Account'")
        print(f"💡 Or run: python tools/manage_servers.py seed --token <YOUR_TOKEN>")


def seed_token(token: str) -> None:
    """
    Seeds a Questrade refresh token via the backend API using curl for zero-dependency reliability.
    """
    print(f"🔑 Seeding Questrade token...")
    try:
        url = f"http://localhost:{PORTS['backend']}/api/questrade/seed"
        data = json.dumps({"refreshToken": token})
        
        # Using curl to ensure it works without extra Python libraries needing installation
        cmd = ["curl", "-s", "-X", "POST", "-H", "Content-Type: application/json", "-d", data, url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            resp = json.loads(result.stdout) if result.stdout else {}
            if resp.get('success'):
                print("   ✅ Token seeded successfully!")
            else:
                print(f"   ❌ Seed failed: {resp.get('error', 'Unknown error')}")
        else:
            print(f"   ❌ Network error (curl exit {result.returncode})")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")


def check_status() -> None:
    """Checks the health and sync status of the toolkit."""
    print("🔍 Toolkit Health Check:")
    for name, port in PORTS.items():
        pids = find_pids(port)
        status = f"✅ Running (PIDs: {pids})" if pids else "❌ Offline"
        print(f"   - {name:8}: {status}")
    
    # Try to get info from backend if online
    if find_pids(PORTS['backend']):
        try:
            url = f"http://localhost:{PORTS['backend']}/api/portfolio/status"
            result = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
            res = json.loads(result.stdout) if result.stdout else {}
            sync_time = res.get('lastSync') or "Never"
            print(f"   - Questrade: {'🔗 Linked' if res.get('lastSync') else '⚠️  Not Linked'}")
            print(f"   - Last Sync: {sync_time}")
        except:
            print("   - Questrade: ❓ Unknown (API error)")
    else:
        print("   - Questrade: ❓ Unknown (Backend offline)")


def main():
    """CLI Entry point with structured argument parsing."""
    parser = argparse.ArgumentParser(description="Toolkit Server Manager")
    parser.add_argument("action", choices=["start", "stop", "restart", "seed", "status"], default="start", help="Operation to perform")
    parser.add_argument("target", nargs="?", choices=["all", "backend", "frontend"], default="all", help="Target component (for start/stop/restart)")
    parser.add_argument("--path", default=".", help="Root path of the project/worktree")
    parser.add_argument("--token", help="Questrade refresh token (for 'seed' action)")
    
    args = parser.parse_args()

    if args.action == "stop":
        stop_servers(args.target)
    elif args.action == "restart":
        stop_servers(args.target)
        time.sleep(1)
        start_servers(args.target, args.path)
    elif args.action == "start":
        start_servers(args.target, args.path)
    elif args.action == "seed":
        if not args.token:
            print("❌ Error: --token <TOKEN> is required for 'seed' action.")
            sys.exit(1)
        # Ensure backend is running before seeding
        if not find_pids(PORTS['backend']):
            print("⚠️  Backend not running. Attempting to start...")
            start_servers('backend', args.path)
            time.sleep(2) # Wait for bootstrap
        seed_token(args.token)
    elif args.action == "status":
        check_status()


if __name__ == "__main__":
    main()
