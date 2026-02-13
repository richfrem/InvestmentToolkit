#!/usr/bin/env python3
"""
manage_servers.py
=====================================

Purpose:
    Provides centralized management for the InvestmentToolkit development servers.
    Handles starting, stopping, and restarting the Node.js backend and Vite frontend.

Layer: Tools / Infrastructure

Usage Examples:
    python tools/manage_servers.py start all
    python tools/manage_servers.py stop backend
    python tools/manage_servers.py restart frontend --path .worktrees/WP05

CLI Arguments:
    action        : Command to execute (start, stop, restart)
    target        : Server to target (all, backend, frontend)
    --path        : Optional worktree path (default: current directory)

Key Functions:
    - start_servers()  : Backgrounds dev servers and directs output to logs.
    - stop_servers()   : Safely terminates processes running on toolkit ports.
    - find_pids()      : Resolves process IDs for specific ports.

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
    }
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
                except ProcessLookupError:
                    pass
        else:
            print(f"   No {t} server detected on port {port}")


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


def main():
    """CLI Entry point with structured argument parsing."""
    parser = argparse.ArgumentParser(description="Toolkit Server Manager")
    parser.add_argument("action", choices=["start", "stop", "restart"], default="start", help="Operation to perform")
    parser.add_argument("target", choices=["all", "backend", "frontend"], default="all", help="Target component")
    parser.add_argument("--path", default=".", help="Root path of the project/worktree")
    
    args = parser.parse_args()

    if args.action == "stop":
        stop_servers(args.target)
    elif args.action == "restart":
        stop_servers(args.target)
        time.sleep(1)
        start_servers(args.target, args.path)
    elif args.action == "start":
        start_servers(args.target, args.path)


if __name__ == "__main__":
    main()
