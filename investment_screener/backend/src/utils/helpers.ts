import net from 'net';
import path from 'path';
import { spawn } from 'child_process';
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE } from './paths';

export const isValidTicker = (ticker: string): boolean => /^[A-Z0-9.\-_]{1,10}$/.test(ticker);

export async function getLiveUsdCadRate(fallback: number): Promise<number> {
    const apiKey = process.env.EXCHANGE_RATE_API_KEY;
    if (apiKey) {
        try {
            const r = await fetch(`https://v6.exchangerate-api.com/v6/${apiKey}/pair/USD/CAD`);
            const d = await r.json();
            if (d.result === 'success') return d.conversion_rate;
        } catch { /* fall through */ }
    }
    return fallback;
}

export function isTradingViewConnected(tvPort = parseInt(process.env.TV_CDP_PORT || '9222', 10)): Promise<boolean> {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(300);
        socket.on('connect', () => { socket.destroy(); resolve(true); });
        socket.on('timeout', () => { socket.destroy(); resolve(false); });
        socket.on('error', () => resolve(false));
        socket.connect(tvPort, 'localhost');
    });
}

export async function getPythonActions(): Promise<Record<string, string>> {
    const scriptPath = path.resolve(__dirname, '../../../../plugins/portfolio-advisor/scripts/portfolio_action.py');
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    return new Promise((resolve) => {
        const proc = spawn(pythonCmd, [scriptPath, '--all', '--portfolio', PORTFOLIO_FILE, '--target', TARGET_PORTFOLIO_FILE]);
        let out = '';
        let err = '';
        proc.stdout.on('data', (d: Buffer) => out += d.toString());
        proc.stderr.on('data', (d: Buffer) => err += d.toString());
        proc.on('close', (code: number) => {
            if (code !== 0) { console.error('[Actions] portfolio_action.py failed:', err); resolve({}); }
            else { try { resolve(JSON.parse(out)); } catch { resolve({}); } }
        });
    });
}
