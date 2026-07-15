/**
 * localAuth.ts - Single-user local API bearer token middleware.
 * 
 * Purpose:
 *   Generates a random token on first run, persists it to .runtime/api-token
 *   (gitignored). All /api/* requests must include:
 *     Authorization: Bearer <token>
 * 
 *   The Vite dev proxy reads the same file and forwards the header automatically.
 *   AI agents and curl scripts: read the token with $(cat .runtime/api-token).
 * 
 *   Exempt: GET /health  (monitoring probes don't need auth)
 * 
 * Layer:
 *   Backend / Middleware / Auth
 * 
 * Key Functions (Index):
 *   - loadOrCreateToken() - Reads cached token from runtime directory or generates a fresh one
 *   - localAuthMiddleware(req, res, next) - Express auth gateway verifying bearer token match
 * 
 * Key Input Dependencies:
 *   - .runtime/api-token (token storage path)
 * 
 * Key Output Dependencies:
 *   - .runtime/api-token
 */
import { Request, Response, NextFunction } from 'express';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const RUNTIME_DIR  = path.resolve(__dirname, '../../../../.runtime');
const TOKEN_FILE   = path.join(RUNTIME_DIR, 'api-token');

function loadOrCreateToken(): string {
    try {
        fs.mkdirSync(RUNTIME_DIR, { recursive: true });
        if (fs.existsSync(TOKEN_FILE)) {
            const tok = fs.readFileSync(TOKEN_FILE, 'utf-8').trim();
            if (tok.length >= 32) return tok;
        }
        const tok = crypto.randomBytes(32).toString('hex');
        fs.writeFileSync(TOKEN_FILE, tok, { mode: 0o600 });
        console.log(`[Auth] New API token written to ${TOKEN_FILE}`);
        return tok;
    } catch (err) {
        // If we can't write the token file (permissions, read-only FS, etc.)
        // fall back to a process-scoped token and warn loudly.
        const tok = crypto.randomBytes(32).toString('hex');
        console.warn(`[Auth] WARNING: Could not write token file (${err}). Using in-process token — restart will generate a new one.`);
        return tok;
    }
}

export const LOCAL_API_TOKEN = loadOrCreateToken();

export function localAuthMiddleware(req: Request, res: Response, next: NextFunction): void {
    // Health probe is always public
    if (req.path === '/health') { next(); return; }

    const authHeader = req.headers['authorization'] ?? '';
    const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';

    if (!token || token !== LOCAL_API_TOKEN) {
        res.status(401).json({ error: 'Unauthorized — missing or invalid local API token.' });
        return;
    }
    next();
}
