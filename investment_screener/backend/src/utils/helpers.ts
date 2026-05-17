import net from 'net';
import { PORTFOLIO_FILE, TARGET_PORTFOLIO_FILE } from './paths';
import { spawnPythonScript } from '../services/bridge';

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
    try {
        const data = await spawnPythonScript('portfolio_action.py', [
            '--all',
            '--portfolio', PORTFOLIO_FILE,
            '--target', TARGET_PORTFOLIO_FILE
        ]);
        return data || {};
    } catch (err) {
        console.error('[Actions] Failed to fetch python actions:', err);
        return {};
    }
}
