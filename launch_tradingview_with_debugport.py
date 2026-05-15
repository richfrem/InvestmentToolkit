#!/usr/bin/env python3
"""
launch_tradingview_with_debugport.py

Relaunches TradingView Desktop with --remote-debugging-port=9222 so that
the Investment Toolkit can connect to it for real-time price quotes.

If TradingView is already running WITHOUT the debug port, it will be stopped
and restarted with the flag automatically.

Usage:
    python3 launch_tradingview_with_debugport.py
"""

import sys
from pathlib import Path

# Delegate to the canonical launcher in the tradingview plugin
sys.path.insert(0, str(Path(__file__).parent / "plugins" / "tradingview" / "scripts"))

import tv_launch
tv_launch.main()
