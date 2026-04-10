import os
import sys
import subprocess
import platform
import signal
import time
import shutil

# --- Configuration & Setup ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(ROOT_DIR, "investment_screener")
os.chdir(APP_DIR)

IS_WINDOWS = platform.system() == "Windows"

# ANSI Colors for output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    CYAN = '\033[0;36m'
    NC = '\033[0m' # No Color

    @staticmethod
    def print(msg, color=NC):
        # On Windows, ANSI codes might require independent enabling, 
        # but modern PowerShell/Git Bash/Windows Terminal support them.
        print(f"{color}{msg}{Colors.NC}")

def run_command(command, shell=False, env=None, check=True):
    """Run a command synchronously."""
    try:
        subprocess.run(command, shell=shell, env=env, check=check)
    except subprocess.CalledProcessError as e:
        Colors.print(f"Error running command: {' '.join(command) if isinstance(command, list) else command}", Colors.RED)
        sys.exit(e.returncode)

def check_command(cmd):
    """Check if a command exists in the path."""
    return shutil.which(cmd) is not None

# --- Main Script ---

def main():
    Colors.print("🚀 Launching Investment Screener...", Colors.GREEN)

    # 1. Check for Node.js
    if not check_command("node"):
        Colors.print("Error: Node.js is not installed.", Colors.RED)
        sys.exit(1)
    
    # 2. Check for Python (implicitly exists since we are running this, but check if we can spawn it)
    #    We will use sys.executable to refer to the current python runner if needed, 
    #    but we are about to setup a venv.

    # 3. Environment Check
    env_file = os.path.join(ROOT_DIR, ".env")
    if not os.path.exists(env_file) and "QUESTRADE_REFRESH_TOKEN" not in os.environ:
        Colors.print("Warning: No .env file found and QUESTRADE_REFRESH_TOKEN not set.", Colors.YELLOW)
        Colors.print("Please copy .env.example to .env and configure it.", Colors.YELLOW)
    
    # 4. Portfolio Configuration Check
    portfolio_path = os.path.join("frontend", "src", "data", "portfolio.json")
    portfolio_example = os.path.join("frontend", "src", "data", "portfolio.json.example")
    
    if not os.path.exists(portfolio_path):
        if os.path.exists(portfolio_example):
            Colors.print("Creating initial portfolio from example...", Colors.YELLOW)
            shutil.copy(portfolio_example, portfolio_path)
        else:
            Colors.print("Warning: No portfolio.json or portfolio.json.example found — skipping.", Colors.YELLOW)

    # 5. Setup Python Virtual Environment
    venv_dir = "venv"
    if not os.path.exists(venv_dir):
        Colors.print("Creating Python virtual environment...", Colors.GREEN)
        run_command([sys.executable, "-m", "venv", "venv"])

    # 6. Activate Virtual Environment (by modifying PATH for child processes)
    Colors.print("Activating virtual environment context...", Colors.GREEN)
    
    env = os.environ.copy()
    if IS_WINDOWS:
        venv_bin = os.path.join(ROOT_DIR, "venv", "Scripts")
    else:
        venv_bin = os.path.join(ROOT_DIR, "venv", "bin")
    
    # Prepend venv bin to PATH
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    # Also set VIRTUAL_ENV legacy variable just in case
    env["VIRTUAL_ENV"] = os.path.join(ROOT_DIR, "venv")
    
    # Verify pip runs from venv
    # We use 'pip' directly now because it should be picked up from the modified PATH
    Colors.print("Installing Python dependencies...", Colors.GREEN)
    
    # Determine pip command name (pip or pip3)
    # Using 'python -m pip' is safer to ensure we use the venv's python
    python_exec = "python" if IS_WINDOWS else "python3"
    
    run_command([python_exec, "-m", "pip", "install", "--upgrade", "pip"], env=env)
    run_command([python_exec, "-m", "pip", "install", "yfinance", "pandas", "uvicorn", "fastapi"], env=env)

    # 7. Install Node dependencies
    Colors.print("Installing Node dependencies...", Colors.GREEN)
    run_command(["npm", "install"], env=env)

    # 8. Build Backend
    Colors.print("Building Backend...", Colors.GREEN)
    run_command(["npm", "run", "build", "-w", "backend"], env=env)

    # 9. Start Services
    Colors.print("Starting Services...", Colors.GREEN)

    # Free ports before starting to avoid EADDRINUSE on restart
    for port in [3001, 5173]:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True, text=True
            )
            pids = result.stdout.strip().split()
            for pid in pids:
                if pid:
                    os.kill(int(pid), signal.SIGKILL)
                    Colors.print(f"  Cleared stale process on :{port} (PID {pid})", Colors.YELLOW)
            if pids:
                time.sleep(0.5)
        except Exception:
            pass

    processes = []
    try:
        # Start Backend
        # We use shell=True to effectively run the npm scripts
        backend_proc = subprocess.Popen(
            ["npm", "run", "start", "-w", "backend"],
            env=env,
            shell=False,
            cwd=APP_DIR
        )
        processes.append(backend_proc)

        # Start Frontend
        # frontend_proc = subprocess.Popen(...) # Removed redundant block
        
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev", "-w", "frontend"],
            env=env,
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
                # On Windows, killing the parent shell=True process might not kill the child node process
                # We might need a more aggressive kill if simply terminating doesn't work,
                # but let's try standard terminate first.
                if IS_WINDOWS:
                    # Windows 'taskkill' can kill the process tree
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
        Colors.print("All services stopped.", Colors.GREEN)

if __name__ == "__main__":
    main()
