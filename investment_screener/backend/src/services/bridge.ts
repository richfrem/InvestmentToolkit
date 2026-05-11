/**
 * bridge.ts (TypeScript Service)
 * =====================================
 *
 * Purpose:
 *     Execution bridge for spawning and managing Python processes from the Node.js backend.
 *     Handles script location resolution, timeout management, and JSON output parsing.
 *
 * Layer: Backend / Services / Bridge
 *
 * Usage Examples:
 *     const data = await spawnPythonScript('fetch_financials.py', ['AAPL']);
 *
 * Key Functions:
 *     - spawnPythonScript() - Spawns a child process for a given Python script and returns parsed JSON results or handles timeouts/errors
 */
import { spawn } from 'child_process';
import path from 'path';

const PYTHON_TIMEOUT_MS = 90_000; // 90 second timeout — cold heatmap load fetches ~32 tickers in parallel (~10-15s)
export const spawnPythonScript = async (scriptName: string, args: string[]): Promise<any> => {
    return new Promise((resolve, reject) => {
        const scriptPath = path.resolve(process.cwd(), 'py_services', scriptName);

        const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
        console.log(`[Bridge] Spawning: ${pythonCommand} ${scriptPath} ${args.join(' ')}`);

        const pythonProcess = spawn(pythonCommand, [scriptPath, ...args]);

        let dataString = '';
        let errorString = '';
        let killed = false;

        const timeout = setTimeout(() => {
            killed = true;
            pythonProcess.kill('SIGTERM');
            reject(new Error(`Python script '${scriptName}' timed out after ${PYTHON_TIMEOUT_MS / 1000}s`));
        }, PYTHON_TIMEOUT_MS);

        pythonProcess.stdout.on('data', (data) => {
            dataString += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorString += data.toString();
        });

        pythonProcess.on('close', (code) => {
            clearTimeout(timeout);
            if (killed) return;

            if (code !== 0) {
                console.error(`[Bridge] Error (Code ${code}): ${errorString}`);
                reject(new Error(`Python script exited with code ${code}: ${errorString}`));
                return;
            }

            try {
                if (!dataString) {
                    resolve(null);
                    return;
                }
                const json = JSON.parse(dataString);
                resolve(json);
            } catch (e) {
                console.error(`[Bridge] Failed to parse JSON: ${dataString}`);
                reject(new Error(`Failed to parse Python output as JSON: ${e}`));
            }
        });

        pythonProcess.on('error', (err) => {
            clearTimeout(timeout);
            reject(new Error(`Failed to spawn Python process: ${err.message}`));
        });
    });
};