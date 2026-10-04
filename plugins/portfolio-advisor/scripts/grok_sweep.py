#!/usr/bin/env python3
"""
grok_sweep.py (Transparent Proxy Forwarder)
===========================================

Purpose:
    Maintains 100% backward compatibility for legacy workflows calling grok_sweep.py.
    Transparently proxies all attribute reads, writes, monkeypatches, and CLI invocations
    directly to news_sweep.py.

Layer: Backend / Python Services / Browser Automation
"""

import sys
import types
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import news_sweep


class _GrokSweepProxy(types.ModuleType):
    """Transparent proxy forwarding all reads and writes to news_sweep."""

    def __getattr__(self, name):
        return getattr(news_sweep, name)

    def __setattr__(self, name, value):
        setattr(news_sweep, name, value)


sys.modules[__name__].__class__ = _GrokSweepProxy

if __name__ == "__main__":
    news_sweep.main()
