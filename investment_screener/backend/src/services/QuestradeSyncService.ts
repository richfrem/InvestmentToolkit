import { spawn } from 'child_process';
import path from 'path';

/**
 * QuestradeSyncService.ts
 * =======================
 * 
 * Purpose:
 *   Manages the lifecycle of the Python Questrade Data Engine.
 *   Provides methods to trigger a full portfolio sync via child_process.
 * 
 * Key Functions:
 *   - runSync() - Spawns the Python engine and returns a promise of completion.
 */

export class QuestradeSyncService {
    // __dirname is backend/src/services/ in dev, backend/dist/services/ in built.
    // Going up two levels always lands at backend/, then src/ has the Python scripts.
    private static PYTHON_SCRIPT_PATH = path.resolve(__dirname, '../../src/QuestradeDataEngine.py');
    private static CACHE_DIR = path.resolve(__dirname, '../../'); // backend/ root where .questrade_cache lives
    private static OUTPUT_FILE = path.resolve(__dirname, '../../../frontend/src/data/portfolio.json');

    /**
     * Spawns the QuestradeDataEngine.py script and waits for completion.
     * 
     * @returns Promise<void> resolves on success, rejects on failure.
     */
    public async runSync(): Promise<void> {
        return new Promise((resolve, reject) => {
            console.log(`[QuestradeSync] Starting sync engine...`);
            console.log(`[QuestradeSync] Script: ${QuestradeSyncService.PYTHON_SCRIPT_PATH}`);

            // Use absolute paths for reliability
            const args = [
                '--cache-dir', QuestradeSyncService.CACHE_DIR,
                '--output', QuestradeSyncService.OUTPUT_FILE
            ];

            // Explicitly pass process.env to ensure QUESTRADE_REFRESH_TOKEN is inherited
            const pythonProcess = spawn('python3', [QuestradeSyncService.PYTHON_SCRIPT_PATH, ...args], {
                env: process.env
            });

            let errorOutput = '';

            pythonProcess.stdout.on('data', (data) => {
                console.log(`[QuestradeSync][Python] ${data.toString().trim()}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                const msg = data.toString().trim();
                errorOutput += msg;
                console.error(`[QuestradeSync][Error] ${msg}`);
            });

            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    console.log(`[QuestradeSync] Sync completed successfully.`);
                    resolve();
                } else {
                    console.error(`[QuestradeSync] Sync failed with exit code ${code}.`);
                    reject(new Error(`Questrade sync engine failed (Exit ${code}): ${errorOutput}`));
                }
            });

            pythonProcess.on('error', (err) => {
                console.error(`[QuestradeSync] Failed to spawn process: ${err.message}`);
                reject(err);
            });
        });
    }
}

export const questradeSyncService = new QuestradeSyncService();
