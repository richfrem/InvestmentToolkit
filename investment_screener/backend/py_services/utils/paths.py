"""
paths.py (Python Utility)
=========================

Purpose:
    Repo-relative path helpers shared across py_services scripts.

Layer: Backend / Python Services / Utilities
"""

import os


def get_temp_dir() -> str:
    """Return the repo-local temp directory, creating it if needed.

    Returns:
        Absolute path to InvestmentToolkit/temp/.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    temp_dir = os.path.join(root, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
