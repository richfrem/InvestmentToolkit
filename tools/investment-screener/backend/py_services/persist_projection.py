"""
persist_projection.py
=====================

Purpose:
    Directly persists a stock valuation projection JSON object to the backend's data store,
    bypassing the API server. Handles validation, file locking, atomic writes, and versioning.
    Designed for multi-agent concurrency: ensures updates only happen if the identity (aiThesis.model) matches.

Methods:
    - validate_projection(data): Enforces Schema compliance (Zod equivalent).
    - ensure_directory(): Creates target directory if missing.
    - get_file_path(ticker): Resolves JSON file path.
    - atomic_write(path, data): Writes to temp file then renames.
    - persist_projection(new_projection, replace_existing=False): Main logic to read, lock, update/append, and write.
    - main(): CLI entry point.

Inputs:
    - STDIN: JSON object matching the Projection schema.
    - ARGUMENTS: 
        --replace: If set, removes any existing entry for this model and appends a fresh one (version 1).

Outputs:
    - Updates/Creates: backend/data/projections/{TICKER}.json
    - STDOUT: Status messages (Created, Updated, Replaced).
    - STDERR: Error messages.

Assumptions:
    - Ticker symbol is valid file system name.
    - `aiThesis.model` is the unique identifier for agent identity within a ticker's projections.
    - File system supports `fcntl` locking (POSIX).
"""

import sys
import json
import os
import fcntl
import math
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTIONS_DIR = os.path.join(BASE_DIR, 'data', 'projections')

def validate_projection(data: Dict[str, Any]) -> None:
    """Validates the projection payload against core constraints."""
    
    # Required top-level fields
    required = ['ticker', 'id', 'scenarios', 'snapshot']
    for field in required:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    # Validate ticker format (simple alphanum check)
    ticker = data.get('ticker', '')
    if not ticker or not ticker.replace('.', '').replace('-', '').isalnum():
        raise ValueError(f"Invalid ticker format: {ticker}")

    # Validate snapshot required fields
    snapshot = data.get('snapshot', {})
    snap_required = ['price', 'currency', 'shares', 'revenue', 'lastActualPS']
    for field in snap_required:
        if field not in snapshot:
            raise ValueError(f"Snapshot missing required field: {field}")

    # Validate numeric types in snapshot
    for field in ['price', 'shares', 'revenue', 'lastActualPS']:
        if field in snapshot and not isinstance(snapshot[field], (int, float)):
             raise ValueError(f"Snapshot field '{field}' must be a number")

    # Validate dataPreferences
    prefs = data.get('dataPreferences', {})
    if not prefs:
        raise ValueError("Missing required field: dataPreferences")
    for field in ['growthBasis', 'marginBasis']:
        if field not in prefs:
            raise ValueError(f"dataPreferences missing required field: {field}")
        if prefs[field] not in ['ttm', 'next', 'current', 'quarterly']:
             raise ValueError(f"Invalid value for dataPreferences.{field}: {prefs[field]}")

    # Validate globalSettings
    globals = data.get('globalSettings', {})
    if not globals:
        raise ValueError("Missing required field: globalSettings")
    for field in ['discountRate', 'timeHorizon']:
        if field not in globals:
            raise ValueError(f"globalSettings missing required field: {field}")
        if not isinstance(globals[field], (int, float)):
             raise ValueError(f"globalSettings field '{field}' must be a number")

    # Validate scenarios
    scenarios = data.get('scenarios', {})
    if not all(k in scenarios for k in ['bear', 'base', 'bull']):
        raise ValueError("Missing one or more scenarios (bear, base, bull)")

    # Validate weights
    weight_sum = sum(scenarios[k].get('weight', 0) for k in ['bear', 'base', 'bull'])
    if abs(weight_sum - 1.0) > 0.01:
        raise ValueError(f"Scenario weights must sum to 1.0 (got {weight_sum})")

    # Validate scenario required fields and types
    scenario_required = ['weight', 'growthRate', 'netMargin', 'exitPE', 'qualityMultiplier', 'shareChange']
    for s_name, s_data in scenarios.items():
        for field in scenario_required:
            if field not in s_data:
                 raise ValueError(f"Scenario '{s_name}' missing required field: {field}")
            if not isinstance(s_data[field], (int, float)):
                 raise ValueError(f"Scenario '{s_name}' field '{field}' must be a number")

def ensure_directory():
    """Ensures the projections directory exists."""
    if not os.path.exists(PROJECTIONS_DIR):
        os.makedirs(PROJECTIONS_DIR)

def get_file_path(ticker: str) -> str:
    """Returns the absolute path to the projection file for a ticker."""
    safe_ticker = "".join(c for c in ticker if c.isalnum() or c in ".-")
    return os.path.join(PROJECTIONS_DIR, f"{safe_ticker}.json")

def atomic_write(path: str, data: List[Dict[str, Any]]) -> None:
    """Writes data to a temporary file and renames it to the target path (atomic)."""
    temp_path = f"{path}.tmp"
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno()) 
    os.rename(temp_path, path)

def persist_projection(new_projection: Dict[str, Any], replace_existing: bool = False) -> None:
    """Main persistence logic."""
    validate_projection(new_projection)
    ensure_directory()
    
    ticker = new_projection['ticker']
    file_path = get_file_path(ticker)
    
    # Open file with exclusive lock for read-update-write cycle
    with open(file_path, 'a+') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX)
            
            # Read existing data
            f.seek(0)
            content = f.read()
            existing_projections = []
            if content.strip():
                try:
                    existing_projections = json.loads(content)
                except json.JSONDecodeError:
                    print(f"Warning: Corrupt or invalid JSON in {file_path}, starting fresh.", file=sys.stderr)
                    existing_projections = []
            
            if not isinstance(existing_projections, list):
                existing_projections = []

            target_model = new_projection.get('aiThesis', {}).get('model')
            
            model_match_index = -1
            if target_model:
                for i, p in enumerate(existing_projections):
                     if p.get('aiThesis', {}).get('model') == target_model:
                         model_match_index = i
                         break
            
            if model_match_index != -1:
                if replace_existing:
                    # Remove existing entry and append new one (fresh start)
                    print(f"Replacing existing entry for model '{target_model}'")
                    del existing_projections[model_match_index]
                    
                    new_projection['version'] = 1
                    if 'savedAt' not in new_projection:
                        from datetime import timezone
                        new_projection['savedAt'] = datetime.now(timezone.utc).isoformat()
                    new_projection['updatedAt'] = new_projection.get('savedAt')
                    
                    existing_projections.append(new_projection)
                else:
                    # Update existing entry for this agent
                    existing_record = existing_projections[model_match_index]
                    current_version = existing_record.get('version', 1)
                    
                    new_projection['version'] = current_version + 1
                    from datetime import timezone
                    new_projection['updatedAt'] = datetime.now(timezone.utc).isoformat()

                    # Preserve creation timestamps if missing
                    if 'savedAt' not in new_projection and 'savedAt' in existing_record:
                        new_projection['savedAt'] = existing_record['savedAt']
                    if 'createdAt' not in new_projection and 'createdAt' in existing_record:
                        new_projection['createdAt'] = existing_record['createdAt']
                    
                    existing_projections[model_match_index] = new_projection
                    print(f"Updated existing projection for model '{target_model}' (v{new_projection['version']})")

            else:
                # No entry found for this agent model -> Insert new
                new_projection['version'] = 1
                if 'savedAt' not in new_projection:
                    from datetime import timezone
                    new_projection['savedAt'] = datetime.now(timezone.utc).isoformat()
                new_projection['updatedAt'] = new_projection.get('savedAt')
                
                existing_projections.append(new_projection)
                print(f"Created new projection for model '{target_model}'")

            # Atomic write
            atomic_write(file_path, existing_projections)
             
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

def main():
    parser = argparse.ArgumentParser(description="Persist stock projection to JSON store.")
    parser.add_argument("--replace", action="store_true", help="Replace existing entry for this model instead of updating.")
    args = parser.parse_args()

    if sys.stdin.isatty():
        print("Usage: cat projection.json | python3 persist_projection.py [--replace]", file=sys.stderr)
        sys.exit(1)
        
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("Error: Empty input", file=sys.stderr)
            sys.exit(1)
            
        projection = json.loads(input_data)
        persist_projection(projection, replace_existing=args.replace)
        print("Success")
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Validation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Internal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
