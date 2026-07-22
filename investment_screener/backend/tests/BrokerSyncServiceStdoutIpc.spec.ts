/**
 * BrokerSyncServiceStdoutIpc.spec.ts
 *
 * Purpose: proves the Wave 3 Domain Data Model v3.2 completion cutover of
 * BrokerSyncService.spawnFetchBroker's IPC return channel from a portfolio.json
 * re-read to parsing the subprocess's stdout as JSON.
 *
 * The former mechanism read portfolio.json.tvSnapshot back off disk after
 * fetch_broker_data.py exited. The new mechanism parses the last non-empty line
 * of the subprocess's stdout as JSON — so it must work even when portfolio.json
 * does NOT exist at all, and must ignore stderr progress noise (mixed-stream
 * safety). These tests use a synthetic fake "python" script, never the live CDP
 * connection or the real domain_model.sqlite/portfolio.json.
 */
import { expect } from 'chai';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { spawnFetchBroker } from '../src/services/BrokerSyncService';

// A fake executable script that mimics fetch_broker_data.py --snapshot's new
// stdout contract: progress lines on stderr, a single JSON blob as the last
// non-empty line of stdout.
function writeFakeScript(body: string): string {
    const p = path.join(os.tmpdir(), `fake-fetch-broker-${Date.now()}-${Math.random()}.sh`);
    fs.writeFileSync(p, `#!/usr/bin/env bash\n${body}\n`, { mode: 0o755 });
    return p;
}

describe('BrokerSyncService.spawnFetchBroker (stdout IPC)', () => {
    const fixture = {
        dataSource: 'tradingview-cdp',
        timestamp: '2026-07-22T00:00:00Z',
        accounts: [{ accountType: 'TFSA', accountId: '1', displayText: 'TFSA' }],
        snapshots: [{ accountType: 'TFSA', balances: { cashUSD: 100 }, positions: [] }],
        positions: [{ symbol: 'MSFT', quantity: 4, avgFillPrice: 410, accountType: 'TFSA', accountId: '1' }],
    };

    it('parses the snapshot from stdout, ignoring stderr progress noise, with no portfolio.json', async () => {
        const json = JSON.stringify(fixture);
        // Emit lots of stderr noise + a final single-line JSON blob on stdout.
        const script = writeFakeScript(
            `>&2 echo "Fetching live balances..."\n` +
            `>&2 echo "Fetching full portfolio snapshot..."\n` +
            `>&2 echo "✓ Persisted 1 position(s) to domain_model.sqlite."\n` +
            `echo '${json}'`,
        );
        const result = await spawnFetchBroker(['--snapshot'], 10_000, { command: 'bash', scriptPath: script });
        expect(result).to.deep.equal(fixture);
        fs.unlinkSync(script);
    });

    it('parses the LAST non-empty stdout line when earlier stray stdout output exists', async () => {
        const json = JSON.stringify(fixture);
        const script = writeFakeScript(
            `echo "some stray refresh_all stdout line"\n` +
            `echo ""\n` +
            `echo '${json}'`,
        );
        const result = await spawnFetchBroker(['--snapshot'], 10_000, { command: 'bash', scriptPath: script });
        expect(result).to.deep.equal(fixture);
        fs.unlinkSync(script);
    });

    it('rejects when the subprocess exits non-zero', async () => {
        const script = writeFakeScript(`>&2 echo "boom"\nexit 1`);
        let threw = false;
        try {
            await spawnFetchBroker(['--snapshot'], 10_000, { command: 'bash', scriptPath: script });
        } catch (e: any) {
            threw = true;
            expect(e.message).to.contain('boom');
        }
        expect(threw).to.equal(true);
        fs.unlinkSync(script);
    });

    it('rejects when stdout has no parseable JSON line', async () => {
        const script = writeFakeScript(`echo "not json at all"`);
        let threw = false;
        try {
            await spawnFetchBroker(['--snapshot'], 10_000, { command: 'bash', scriptPath: script });
        } catch {
            threw = true;
        }
        expect(threw).to.equal(true);
        fs.unlinkSync(script);
    });
});
