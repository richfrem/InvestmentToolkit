#!/usr/bin/env python3
"""
generate_grok_prompt.py (Transparent Proxy Forwarder)
=====================================================

Purpose:
    Maintains 100% backward compatibility for legacy workflows calling generate_grok_prompt.py.
    Transparently proxies all attribute reads, writes, monkeypatches, and CLI invocations
    directly to generate_news_prompt.py.

Layer: Backend / Python Services / AI Prompt Engineering
"""

import sys
import types
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generate_news_prompt


class _GenerateGrokPromptProxy(types.ModuleType):
    """Transparent proxy forwarding all reads and writes to generate_news_prompt."""

    def __getattr__(self, name):
        return getattr(generate_news_prompt, name)

    def __setattr__(self, name, value):
        setattr(generate_news_prompt, name, value)


sys.modules[__name__].__class__ = _GenerateGrokPromptProxy

if __name__ == "__main__":
    generate_news_prompt.main()
