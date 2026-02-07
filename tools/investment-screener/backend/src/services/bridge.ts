import { spawn } from 'child_process';
import path from 'path';

/**
 * Spawns a Python script and returns the JSON output.
 * @param scriptName Name of the script in py_services folder (e.g., 'fetch_financials.py')
 * @param args Array of arguments to pass to the script
 */
export const spawnPythonScript = async (scriptName: string, args: string[]): Promise<any> => {
    return new Promise((resolve, reject) => {
        // Resolve absolute path to the script
        // Assumes script is running from dist/ or src/ and py_services is sibling to src/
        // Adjust based on strict folder structure:
        // backend/
        //   src/services/bridge.ts
        //   py_services/

        // Check if we are in dist (built) or src (dev)
        const isCompiled = __dirname.includes('dist');
        const rootDir = isCompiled ? path.join(__dirname, '../../..') : path.join(__dirname, '../..');
        // If running from src/services: ../.. -> backend/
        // If running from dist/services: ../../.. -> backend/ (assuming dist/services structure)

        // Safer to resolve from CWD if started via npm run start
        // tools/investment-screener/backend
        const scriptPath = path.resolve(process.cwd(), 'py_services', scriptName);

        console.log(`[Bridge] Spawning: python3 ${scriptPath} ${args.join(' ')}`);

        const pythonProcess = spawn('source ../venv/bin/activate && python3', [scriptPath, ...args], {
            shell: true
        });
        // Note: Virtualenv activation in spawn might be tricky. 
        // Better to assume `python3` is the venv python if running via startup.sh
        // OR just use 'python3' and rely on environment.

        // Let's rely on the environment being set up correctly (via startup.sh) or just 'python3'
        // If startup.sh activated venv, then 'python3' is correct.

        const process_simple = spawn('python3', [scriptPath, ...args]);

        let dataString = '';
        let errorString = '';

        process_simple.stdout.on('data', (data) => {
            dataString += data.toString();
        });

        process_simple.stderr.on('data', (data) => {
            errorString += data.toString();
        });

        process_simple.on('close', (code) => {
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
    });
};
