#!/usr/bin/env python3
"""
cli.py
=====================================

Purpose:
    Main entry point for the InvestmentToolkit Command System.
    Provides unified access to vector database operations, context bundling,
    and agent workflow orchestration.

Layer: Tools / Orchestrator

Usage Examples:
    # Vector Operations
    python tools/cli.py ingest --incremental --hours 24
    python tools/cli.py query "Apple revenue growth"
    python tools/cli.py vector-cleanup --apply

    # Context & Bundling
    python tools/cli.py context init --target AAPL --type generic
    python tools/cli.py context add --path tools/py_services/fetch_financials.py
    python tools/cli.py context bundle

    # Workflows
    python tools/cli.py workflow start stock-analysis --target AAPL
    python tools/cli.py workflow retrospective

Key Commands:
    - ingest      : Ingest files into Vector DB.
    - query       : Semantic search against Vector DB + RLM cache.
    - context     : Manage context bundles (init, add, remove, bundle).
    - workflow    : Manage agent lifecycle (start, retrospective).
    - speckit     : Proxy to Spec-Kitty framework bridge.

Related:
    - manage_tool_inventory.py
    - manage_servers.py
"""

import sys
import argparse
import json
import os
import subprocess
from pathlib import Path

# Add project root to sys.path
CLI_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CLI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import path resolver
try:
    from tools.investigate.utils.path_resolver import resolve_path
except ImportError:
    sys.path.append(str(PROJECT_ROOT))
    from tools.investigate.utils.path_resolver import resolve_path

# Resolve Directories
SHARED_DIR = Path(resolve_path("tools/shared"))
RETRIEVE_DIR = Path(resolve_path("tools/retrieve/bundler"))
VECTOR_TOOLS_DIR = Path(resolve_path("tools/retrieve/vector"))
INVENTORIES_DIR = Path(resolve_path("tools/curate/inventories"))
RLM_DIR = Path(resolve_path("tools/retrieve/rlm"))
ORCHESTRATOR_DIR = Path(resolve_path("tools/orchestrator"))

# Add directories to sys.path
for d in [SHARED_DIR, RETRIEVE_DIR, INVENTORIES_DIR, RLM_DIR, ORCHESTRATOR_DIR]:
    if str(d) not in sys.path:
        sys.path.append(str(d))

from workflow_manager import WorkflowManager


def main():
    parser = argparse.ArgumentParser(description="InvestmentToolkit Unified CLI")
    subparsers = parser.add_subparsers(dest="command")

    # --- 1. VECTOR DATABASE ---
    ingest_parser = subparsers.add_parser("ingest", help="Ingest files into Vector DB")
    ingest_parser.add_argument("--full", action="store_true", help="Full ingestion (purge and rebuild)")
    ingest_parser.add_argument("--incremental", action="store_true", help="Incremental ingestion")
    ingest_parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    ingest_parser.add_argument("--cleanup", action="store_true", help="Run cleanup after ingestion")
    ingest_parser.add_argument("--v", action="store_true", help="Verbose output")

    query_parser = subparsers.add_parser("query", help="Query Knowledge Base (Semantic Search)")
    query_parser.add_argument("text", help="Query text")

    vector_cleanup_parser = subparsers.add_parser("vector-cleanup", help="Clean stale entries from Vector DB")
    vector_cleanup_parser.add_argument("--apply", action="store_true", help="Perform deletion")
    vector_cleanup_parser.add_argument("--prune-orphans", action="store_true", help="Remove orphans")

    # --- 2. CONTEXT MANAGEMENT ---
    context_parser = subparsers.add_parser("context", help="Manage Perspective Context Bundles")
    context_subparsers = context_parser.add_subparsers(dest="context_action")
    
    # context init
    c_init = context_subparsers.add_parser("init", help="Initialize a fresh manifest")
    c_init.add_argument("--target", required=True, help="Target ID (e.g. AAPL)")
    c_init.add_argument("--type", default="generic", help="Bundle type")

    # context add
    c_add = context_subparsers.add_parser("add", help="Add file to manifest")
    c_add.add_argument("--path", required=True)
    c_add.add_argument("--note", default="")

    # context remove
    c_rem = context_subparsers.add_parser("remove", help="Remove file from manifest")
    c_rem.add_argument("--path", required=True)

    # context list
    context_subparsers.add_parser("list", help="List manifest files")

    # context bundle
    c_bun = context_subparsers.add_parser("bundle", help="Generate final markdown bundle")
    c_bun.add_argument("--output", help="Optional output path")

    # --- 3. TOOLS & WORKFLOWS ---
    tools_parser = subparsers.add_parser("tools", help="Discover and Manage CLI Tools")
    tools_subparsers = tools_parser.add_subparsers(dest="tools_action")
    tools_subparsers.add_parser("list", help="List all tools")
    t_search = tools_subparsers.add_parser("search", help="Search for tools")
    t_search.add_argument("keyword")

    wf_parser = subparsers.add_parser("workflow", help="Agent Workflow Orchestration")
    wf_subparsers = wf_parser.add_subparsers(dest="workflow_action")
    wf_start = wf_subparsers.add_parser("start", help="Start a new workflow")
    wf_start.add_argument("name")
    wf_start.add_argument("--target")
    wf_subparsers.add_parser("retrospective", help="Run Self-Retrospective")

    # --- 4. SPECKIT BRIDGE ---
    sk_parser = subparsers.add_parser("speckit", help="Spec-Kitty Bridge Proxy")
    sk_parser.add_argument("args", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    # --- EXECUTION LOGIC ---
    if args.command == "speckit":
        if not args.args:
            print("❌ No arguments for speckit.")
            sys.exit(1)
        cmd = [sys.executable, "-c", "import sys; from specify_cli import main; sys.argv[0] = 'spec-kitty'; main()"] + args.args
        subprocess.run(cmd)

    elif args.command == "ingest":
        script = str(Path(resolve_path("tools/codify/vector")) / "ingest.py")
        cmd = [sys.executable, script]
        if args.full: cmd.append("--full")
        if args.incremental: cmd.append("--incremental")
        if args.hours: cmd.extend(["--hours", str(args.hours)])
        if args.cleanup: cmd.append("--cleanup")
        if args.v: cmd.append("--v")
        subprocess.run(cmd)

    elif args.command == "query":
        print(f"🔍 Semantic Search (Vector DB):")
        subprocess.run([sys.executable, str(VECTOR_TOOLS_DIR / "query.py"), args.text])
        print(f"\n📚 Cache Search (RLM):")
        subprocess.run([sys.executable, str(RLM_DIR / "query_cache.py"), args.text])

    elif args.command == "vector-cleanup":
        script = str(Path(resolve_path("tools/curate/vector")) / "cleanup.py")
        cmd = [sys.executable, script]
        if args.apply: cmd.append("--apply")
        if args.prune_orphans: cmd.append("--prune-orphans")
        subprocess.run(cmd)

    elif args.command == "context":
        script = str(RETRIEVE_DIR / "manifest_manager.py")
        if args.context_action == "init":
            subprocess.run([sys.executable, script, "init", "--bundle-title", args.target, "--type", args.type])
            # Auto-bundle after init as a convenience
            subprocess.run([sys.executable, script, "bundle"])
        elif args.context_action == "add":
            subprocess.run([sys.executable, script, "add", "--path", args.path, "--note", args.note])
        elif args.context_action == "remove":
            subprocess.run([sys.executable, script, "remove", "--path", args.path])
        elif args.context_action == "list":
            subprocess.run([sys.executable, script, "list"])
        elif args.context_action == "bundle":
            cmd = [sys.executable, script, "bundle"]
            if args.output: cmd.extend(["--output", args.output])
            subprocess.run(cmd)

    elif args.command == "tools":
        script = str(INVENTORIES_DIR / "manage_tool_inventory.py")
        cmd = [sys.executable, script, args.tools_action]
        if args.tools_action == "search":
            cmd.append(args.keyword)
        subprocess.run(cmd)

    elif args.command == "workflow":
        manager = WorkflowManager()
        if args.workflow_action == "start":
            manager.start_workflow(args.name, target=args.target)
        elif args.workflow_action == "retrospective":
            manager.run_retrospective()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
