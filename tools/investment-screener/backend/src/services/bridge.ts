import { spawn } from 'child_process';
import path from 'path';

const PYTHON_TIMEOUT_MS = 30_000; // 30 second timeout for Python scripts

/**
 * Spawns a Python script and returns the JSON output.
 * @param scriptName Name of the script in py_services folder (e.g., 'fetch_financials.py')
 * @param args Array of arguments to pass to the script
 */
export const spawnPythonScript = async (scriptName: string, args: string[]): Promise<any> => {
    return new Promise((resolve, reject) => {
        const scriptPath = path.resolve(process.cwd(), 'py_services', scriptName);

        console.log(`[Bridge] Spawning: python3 ${scriptPath} ${args.join(' ')}`);

        const pythonProcess = spawn('python3', [scriptPath, ...args]);

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