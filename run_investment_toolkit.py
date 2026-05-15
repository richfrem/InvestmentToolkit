#!/usr/bin/env python
"""
run_investment_toolkit.py (CLI)
=====================================

Purpose:
    Unified startup script for the Investment Toolkit suite.
    Handles virtual environment setup, dependency installation (Node & Python),
    backend building, and concurrent service orchestration (Frontend & Backend).

Layer: Codify

Usage Examples:
    python3 run_investment_toolkit.py

Supported Object Types:
    N/A

CLI Arguments:
    None

Input Files:
    - .env: Environment configuration
    - investment_screener/backend/data/portfolio.json: User portfolio data

Output:
    - Running services on localhost:3001 and localhost:5173
    - Logs to stdout/stderr

Key Functions:
    - main(): Entry point for the startup sequence
    - run_command(): Synchronous command execution helper
    - check_command(): Path-based command existence check

Script Dependencies:
    - Node.js (npm)
    - Python 3.8+

Consumed by:
    - Developers for local development and testing
"""

import os
import sys
import subprocess
import platform
import signal
import time
import shutil
from typing import List, Optional, Dict, Any

# --- Configuration & Setup ---
ROOT_DIR: str = os.path.dirname(os.path.abspath(__file__))
APP_DIR: str = os.path.join(ROOT_DIR, "investment_screener")

# Ensure we operate relative to the app directory for npm commands
os.chdir(APP_DIR)

IS_WINDOWS: bool = platform.system() == "Windows"

# Colors class
class Colors:
    """ANSI color codes for terminal output."""
    GREEN: str = '\033[0;32m'
    YELLOW: str = '\033[1;33m'
    RED: str = '\033[0;31m'
    CYAN: str = '\033[0;36m'
    NC: str = '\033[0m' # No Color

    @staticmethod
    def print(msg: str, color: str = NC) -> None:
        """
        Prints a colored message to the terminal.

        Args:
            msg: The message to print.
            color: ANSI color code.
        """
        print(f"{color}{msg}{Colors.NC}")

# run_command function
def run_command(
    command: List[str], 
    shell: bool = False, 
    env: Optional[Dict[str, str]] = None, 
    check: bool = True
) -> None:
    """
    Run a command synchronously.

    Args:
        command: List of command arguments.
        shell: Whether to use the shell.
        env: Environment variables for the child process.
        check: If True, raises CalledProcessError on non-zero exit.

    Raises:
        SystemExit: If the command fails and check is True.
    """
    try:
        subprocess.run(command, shell=shell, env=env, check=check)
    except subprocess.CalledProcessError as e:
        Colors.print(f"Error running command: {' '.join(command)}", Colors.RED)
        sys.exit(e.returncode)

# check_command function
def check_command(cmd: str) -> bool:
    """
    Check if a command exists in the system PATH.

    Args:
        cmd: Command name to check.

    Returns:
        True if the command exists, False otherwise.
    """
    return shutil.which(cmd) is not None

# clear_ports function
def clear_ports(ports: List[int]) -> None:
    """
    Attempt to kill processes listening on the specified ports.

    Args:
        ports: List of port numbers to clear.
    """
    for port in ports:
        try:
            if not IS_WINDOWS:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True, text=True
                )
                pids = result.stdout.strip().split()
                for pid in pids:
                    if pid:
                        os.kill(int(pid), signal.SIGKILL)
                        Colors.print(f"  Cleared stale process on :{port} (PID {pid})", Colors.YELLOW)
            else:
                # Windows port clearing
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True, text=True
                )
                for line in result.stdout.splitlines():
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        Colors.print(f"  Cleared stale process on :{port} (PID {pid})", Colors.YELLOW)
            
            time.sleep(0.5)
        except Exception:
            pass

# setup_virtual_env function
def setup_virtual_env(venv_dir: str, env: Dict[str, str]) -> None:
    """
    Creates and populates the Python virtual environment.

    Args:
        venv_dir: Path to the venv directory.
        env: Environment variables dictionary to be updated.
    """
    if not os.path.exists(venv_dir):
        Colors.print("Creating Python virtual environment...", Colors.GREEN)
        run_command([sys.executable, "-m", "venv", venv_dir])

    Colors.print("Activating virtual environment context...", Colors.GREEN)
    
    if IS_WINDOWS:
        venv_bin = os.path.join(ROOT_DIR, venv_dir, "Scripts")
    else:
        venv_bin = os.path.join(ROOT_DIR, venv_dir, "bin")
    
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = os.path.join(ROOT_DIR, venv_dir)
    
    Colors.print("Installing Python dependencies...", Colors.GREEN)
    python_exec = "python" if IS_WINDOWS else "python3"

    run_command([python_exec, "-m", "pip", "install", "--upgrade", "pip"], env=env)

    # Install from compiled requirements.txt if present; otherwise fall back to requirements.in.
    # Always run `pip-compile requirements.in -o requirements.txt` after adding a new dep to requirements.in.
    req_txt = os.path.join(ROOT_DIR, "requirements.txt")
    req_in  = os.path.join(ROOT_DIR, "requirements.in")
    if os.path.exists(req_txt):
        run_command([python_exec, "-m", "pip", "install", "-r", req_txt], env=env)
    elif os.path.exists(req_in):
        Colors.print("Warning: requirements.txt not found — installing from requirements.in (unpinned).", Colors.YELLOW)
        run_command([python_exec, "-m", "pip", "install", "-r", req_in], env=env)
    else:
        Colors.print("Warning: No requirements file found — installing minimal fallback deps.", Colors.YELLOW)
        run_command([python_exec, "-m", "pip", "install", "yfinance", "pandas", "uvicorn", "fastapi",
                     "cryptography", "keyring"], env=env)

def _launch_tradingview() -> None:
    """Delegate to tv_launch.py — single source of truth for TradingView CDP launch."""
    tv_launcher = os.path.join(ROOT_DIR, "plugins", "tradingview", "scripts", "tv_launch.py")
    if not os.path.exists(tv_launcher):
        Colors.print("  TradingView: launcher not found — skipping.", Colors.YELLOW)
        return
    try:
        subprocess.run([sys.executable, tv_launcher], check=False)
    except Exception as e:
        Colors.print(f"  TradingView: launch failed ({e}) — yfinance fallback active.", Colors.YELLOW)


# main function
def main() -> None:
    """
    Main execution loop for launching the toolkit.
    """
    Colors.print("🚀 Launching Investment Screener...", Colors.GREEN)

    # 1. Check for Node.js
    if not check_command("node"):
        Colors.print("Error: Node.js is not installed.", Colors.RED)
        sys.exit(1)
    
    # 2. Environment Check
    env_file = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_file) and "QUESTRADE_REFRESH_TOKEN" not in os.environ:
        Colors.print("Warning: No .env file found and QUESTRADE_REFRESH_TOKEN not set.", Colors.YELLOW)
        Colors.print("Please copy .env.example to .env and configure it.", Colors.YELLOW)
    
    # 3. Portfolio Configuration Check
    portfolio_path = os.path.join("frontend", "src", "data", "portfolio.json")
    portfolio_example = os.path.join("frontend", "src", "data", "portfolio.json.example")
    
    if not os.path.exists(portfolio_path):
        if os.path.exists(portfolio_example):
            Colors.print("Creating initial portfolio from example...", Colors.YELLOW)
            shutil.copy(portfolio_example, portfolio_path)
        else:
            Colors.print("Warning: No portfolio.json or portfolio.json.example found — skipping.", Colors.YELLOW)

    # 4. Setup venv
    process_env = os.environ.copy()
    setup_virtual_env(os.path.join(ROOT_DIR, "venv"), process_env)

    # 5. Pre-flight: fix root-owned node_modules (caused by accidental sudo npm/rm)
    node_modules_dir = os.path.join(ROOT_DIR, "investment_screener", "node_modules")
    if os.path.exists(node_modules_dir) and not IS_WINDOWS:
        import pwd
        current_user = pwd.getpwuid(os.getuid()).pw_name
        result = subprocess.run(
            ["find", node_modules_dir, "-maxdepth", "1", "-user", "root"],
            capture_output=True, text=True
        )
        root_owned = [l for l in result.stdout.strip().splitlines() if l]
        if root_owned:
            Colors.print(
                f"⚠️  {len(root_owned)} node_modules packages are owned by root — fixing permissions...",
                Colors.YELLOW
            )
            fix_result = subprocess.run(
                ["sudo", "chown", "-R", f"{current_user}", node_modules_dir],
                check=False
            )
            if fix_result.returncode != 0:
                Colors.print("❌ Permission fix failed. Please run this manually, then re-run:", Colors.RED)
                Colors.print(
                    f"   sudo chown -R {current_user} {node_modules_dir}",
                    Colors.YELLOW
                )
                sys.exit(1)
            Colors.print("✅ node_modules permissions restored.", Colors.GREEN)

    # 5. Install Node dependencies
    Colors.print("Installing Node dependencies...", Colors.GREEN)
    run_command(["npm", "install"], env=process_env)

    # 5b. Python dependency preflight — fail fast before starting servers
    Colors.print("Verifying Python dependencies...", Colors.GREEN)
    _required_modules = ["keyring", "cryptography", "yfinance", "pandas"]
    _python_exec = "python" if IS_WINDOWS else "python3"
    _missing = []
    for _mod in _required_modules:
        result = subprocess.run(
            [_python_exec, "-c", f"import {_mod}"],
            env=process_env,
            capture_output=True
        )
        if result.returncode != 0:
            _missing.append(_mod)
    if _missing:
        Colors.print(f"❌ Missing Python modules: {', '.join(_missing)}", Colors.RED)
        Colors.print("Run: pip install " + " ".join(_missing), Colors.YELLOW)
        Colors.print("Or add missing packages to requirements.in and re-run pip-compile.", Colors.YELLOW)
        sys.exit(1)
    Colors.print("✅ Python dependencies OK.", Colors.GREEN)

    # 5c. Launch TradingView Desktop (non-blocking, best-effort)
    Colors.print("Launching TradingView Desktop...", Colors.GREEN)
    _launch_tradingview()

    # 6. Build Backend
    Colors.print("Building Backend...", Colors.GREEN)
    run_command(["npm", "run", "build", "-w", "backend"], env=process_env)

    # 7. Start Services
    Colors.print("Starting Services...", Colors.GREEN)
    clear_ports([3001, 5173])

    processes: List[subprocess.Popen] = []
    try:
        # Start Backend
        backend_proc = subprocess.Popen(
            ["npm", "run", "start", "-w", "backend"],
            env=process_env,
            shell=False,
            cwd=APP_DIR
        )
        processes.append(backend_proc)

        # Start Frontend
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev", "-w", "frontend"],
            env=process_env,
            shell=False,
            cwd=APP_DIR
        )
        processes.append(frontend_proc)

        Colors.print("✅ Services Running!", Colors.GREEN)
        Colors.print("Backend:  http://localhost:3001")
        Colors.print("Frontend: http://localhost:5173")
        Colors.print("\nPress Ctrl+C to stop all services.", Colors.CYAN)

        # Wait for processes
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)

    except KeyboardInterrupt:
        Colors.print("\nShutting down services...", Colors.YELLOW)
    finally:
        for p in processes:
            if p.poll() is None:
                if IS_WINDOWS:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
        Colors.print("All services stopped.", Colors.GREEN)

if __name__ == "__main__":
    main()
