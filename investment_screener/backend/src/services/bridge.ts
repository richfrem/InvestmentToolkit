/**
 * bridge.ts - Express to Python analytical script bridge.
 * 
 * Purpose:
 *   Execution bridge for spawning and managing Python processes from the Node.js backend.
 *   Handles script location resolution, timeout management, and JSON output parsing.
 * 
 * Layer:
 *   Backend / Services / Bridge
 * 
 * Usage Examples:
 *   const data = await spawnPythonScript('fetch_financials.py', ['AAPL']);
 * 
 * Key Functions (Index):
 *   - _cacheKey(scriptName, args) - Generates a cache key for deduplication
 *   - spawnPythonScript(scriptName, args) - Deduplicated entry point for running a Python analytical script
 *   - _spawnRaw(scriptName, args) - Spawns a child process for a given Python script, returning parsed JSON
 * 
 * Key Input Dependencies:
 *   - investment_screener/backend/py_services/ (location of executable Python scripts)
 * 
 * Key Output Dependencies:
 *   None
 */
import { spawn } from 'child_process';
import path from 'path';

const PYTHON_TIMEOUT_MS = 90_000;
// __dirname is backend/src/services/ in dev, backend/dist/services/ in built.
const PY_SERVICES_DIR = path.resolve(__dirname, '../../py_services');

// ── Circuit breaker: in-flight deduplication + stale cache ───────────────────
// If a caller requests the same script+args while a prior call is still running,
// the second caller waits on the same Promise instead of spawning a second process.
// On timeout the last successful result is returned (with a `stale: true` flag)
// so the frontend never hangs indefinitely.
const _inflight = new Map<string, Promise<any>>();
const _lastResult = new Map<string, { ts: number; value: any }>();

function _cacheKey(scriptName: string, args: string[]): string {
    return `${scriptName}|${args.join('|')}`;
}

export const spawnPythonScript = async (scriptName: string, args: string[]): Promise<any> => {
    const key = _cacheKey(scriptName, args);

    const existing = _inflight.get(key);
    if (existing) {
        console.log(`[Bridge] Deduplicating in-flight call: ${scriptName}`);
        return existing;
    }

    const promise = _spawnRaw(scriptName, args)
        .then(result => {
            _lastResult.set(key, { ts: Date.now(), value: result });
            return result;
        })
        .catch((err: Error) => {
            const cached = _lastResult.get(key);
            if (cached) {
                console.warn(`[Bridge] ${scriptName} failed (${err.message}) — returning cached result from ${Math.round((Date.now() - cached.ts) / 1000)}s ago`);
                return { ...cached.value, stale: true, staleReason: err.message };
            }
            throw err;
        })
        .finally(() => _inflight.delete(key));

    _inflight.set(key, promise);
    return promise;
};

const _spawnRaw = async (scriptName: string, args: string[]): Promise<any> => {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(PY_SERVICES_DIR, scriptName);

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