# ADR 017: Multi-Language Bridge Pattern

## Status
Proposed (Inferred from existing codebase)

## Context
Financial data retrieval and analysis are most efficient in Python, but the primary application interface is built in Node.js/React. We need a way to combine these environments without the complexity of a full microservices architecture for a local tool.

## Decision
Use a **CLI-based Bridge Pattern**:
1. Node.js backend invokes Python scripts via shell commands using `child_process.exec` or `spawn`.
2. Communication occurs via standard output (stdout), where Python scripts return structured JSON data.
3. Node.js parses the JSON and returns it to the frontend.

## Consequences
- **Pros**:
    - Simple to implement and debug.
    - No need for persistent Python web servers (FastAPI/Flask) for simple data tasks.
    - Easy to add new Python services as standalone scripts.
- **Cons**:
    - No shared memory between Node.js and Python.
    - Cold-start overhead for the Python interpreter on every call.
