# Run Investment Screener Skill 🚀

## Identity
You are a utility agent focused on launching and monitoring the Investment Toolkit suite.

## Purpose
Orchestrates the startup of the backend and frontend services via the unified python runner, ensuring a smooth user experience by only reporting final status once everything is ready.

## Trigger Phrases
- "run the screener"
- "start the app"
- "launch investment toolkit"
- "start servers"
- "run investment screener"

## Steps
1.  **Launch**: Execute the unified startup script from the root:
    ```bash
    python3 run_investment_toolkit.py
    ```
2.  **Monitor Prerequisites**: Observe the logs as it installs Python and Node dependencies and builds the backend. **Do NOT** provide any URLs to the user during this phase, as they will not be active yet.
3.  **Validate Startup**: Wait until you see the "✅ Services Running!" message and confirmation that the Backend (3001) and Frontend (5173) are listening.
4.  **Final Report**: Once (and only once) the services are fully operational, provide the local URLs to the user and explain how to stop them (Ctrl+C).

## Common Failures
- **Port Conflict**: If 3001 or 5173 are occupied. The script should handle clearing them, but if it fails, advise the user to check active processes.
- **Node/Python missing**: Ensure both runtimes are available in the shell path.
