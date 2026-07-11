/**
 * src/routes/thirteenf.ts
 * =======================
 *
 * Purpose:
 *   Serves parsed SA LP 13F holdings, diffs, and summaries from local JSON files.
 *
 * Key Functions:
 *   - resolveTicker() - Resolves CUSIP/Name to a canonical ticker symbol
 *   - loadHoldingsFile() - Reads and maps holdings JSON for an accession number
 */
import { Router } from 'express';
import fs from 'fs';
import path from 'path';

const router = Router();

const DATA_DIR  = path.resolve(__dirname, '../../data/13f');
const INDEX_FILE = path.join(DATA_DIR, '0002045724_index.json');
const DIFF_FILE  = path.join(DATA_DIR, '0002045724_diff.json');

// CUSIP → ticker symbol mapping for SA LP holdings
const CUSIP_TICKER: Record<string, string> = {
    '92189F676': 'SMH',
    '67066G104': 'NVDA',
    '68389X105': 'ORCL',
    '11135F101': 'AVGO',
    '007903107': 'AMD',
    '595112103': 'MU',
    '874039100': 'TSM',
    '04523Y198': 'ASML',
    '219350105': 'GLW',
    '09075V102': 'BE',
    '80004C101': 'SNDK',
    '21875D100': 'CRWV',
    '46267X109': 'IREN',
    '21878Q107': 'CORZ',
    '03823U101': 'APLD',
    '767292103': 'RIOT',
    '18491F100': 'CLSK',
    '09166M108': 'BITF',
    '09164X101': 'BTDR',
    '73931Y109': 'PSIX',
    '96348W100': 'WYFI',
    '05329W102': 'BW',
    '74348T102': 'PUMP',
    '83417X100': 'SLNC',
    '87261Q100': 'T1E',
    '81942E102': 'SHRN',
    '43376L101': 'HIVE',
    '458140100': 'INTC',
};

// Name-fragment fallback for unmapped CUSIPs
const NAME_TICKER: Record<string, string> = {
    'VANECK': 'SMH', 'NVIDIA': 'NVDA', 'ORACLE': 'ORCL', 'BROADCOM': 'AVGO',
    'ADVANCED MICRO': 'AMD', 'MICRON': 'MU', 'TAIWAN SEMI': 'TSM', 'ASML': 'ASML',
    'CORNING': 'GLW', 'BLOOM ENERGY': 'BE', 'SANDISK': 'SNDK', 'COREWEAVE': 'CRWV',
    'IREN': 'IREN', 'CORE SCIENTIFIC': 'CORZ', 'APPLIED DIGITAL': 'APLD',
    'RIOT PLATFORMS': 'RIOT', 'CLEANSPARK': 'CLSK', 'BITFARMS': 'BITF',
    'BITDEER': 'BTDR', 'POWER SOLUTIONS': 'PSIX', 'WHITEFIBER': 'WYFI',
    'BABCOCK': 'BW', 'PROPETRO': 'PUMP', 'SOLARIS': 'SLNC',
    'T1 ENERGY': 'T1E', 'SHARONAI': 'SHRN', 'HIVE DIGITAL': 'HIVE', 'INTEL': 'INTC',
};

function resolveTicker(cusip: string, name: string): string {
    if (CUSIP_TICKER[cusip]) return CUSIP_TICKER[cusip];
    const upper = name.toUpperCase();
    for (const [frag, ticker] of Object.entries(NAME_TICKER)) {
        if (upper.includes(frag)) return ticker;
    }
    return name.split(' ')[0].slice(0, 6);
}

function loadHoldingsFile(accession: string): any[] {
    const safe = accession.replace(/-/g, '');
    const file = path.join(DATA_DIR, `${safe}.json`);
    if (!fs.existsSync(file)) return [];
    const d = JSON.parse(fs.readFileSync(file, 'utf-8'));
    return (d.holdings ?? []).map((h: any) => ({
        ...h,
        ticker: resolveTicker(h.cusip, h.name),
    }));
}

router.get('/summary', (_req, res) => {
    try {
        if (!fs.existsSync(INDEX_FILE)) { res.status(404).json({ error: '13F index not found' }); return; }

        const index: any[] = JSON.parse(fs.readFileSync(INDEX_FILE, 'utf-8'));
        const latest = index[0];
        const prev   = index[1] ?? null;

        const accession = latest.accession.replace(/-/g, '');
        const holdingsFile = path.join(DATA_DIR, `${accession}.json`);
        if (!fs.existsSync(holdingsFile)) { res.status(404).json({ error: '13F holdings file not found' }); return; }

        const raw = JSON.parse(fs.readFileSync(holdingsFile, 'utf-8'));
        const holdings = (raw.holdings ?? []).map((h: any) => ({
            ...h,
            ticker: resolveTicker(h.cusip, h.name),
        }));

        // Married put detection: tickers that appear as BOTH long (null) AND put
        const putTickers  = new Set(holdings.filter((h: any) => h.put_call === 'Put').map((h: any) => h.ticker));
        const longTickers = new Set(holdings.filter((h: any) => h.put_call === null).map((h: any) => h.ticker));
        const marriedPutTickers = [...longTickers].filter(t => putTickers.has(t));

        // Annotate holdings with married_put flag and put_value
        const putValueByTicker: Record<string, number> = {};
        holdings.filter((h: any) => h.put_call === 'Put').forEach((h: any) => {
            putValueByTicker[h.ticker] = (putValueByTicker[h.ticker] ?? 0) + h.value_usd;
        });

        const enrichedHoldings = holdings.map((h: any) => ({
            ...h,
            married_put: h.put_call === null && putTickers.has(h.ticker),
            put_value:   h.put_call === null ? (putValueByTicker[h.ticker] ?? 0) : 0,
        }));

        const diff = fs.existsSync(DIFF_FILE)
            ? JSON.parse(fs.readFileSync(DIFF_FILE, 'utf-8'))
            : null;

        // Enrich diff entries with tickers and married put flag
        function enrichDiff(arr: any[]) {
            return (arr ?? []).map((h: any) => {
                const ticker = resolveTicker(h.cusip ?? '', h.name ?? '');
                return {
                    ...h,
                    ticker,
                    married_put: h.put_call === null && putTickers.has(ticker),
                    put_value:   h.put_call === null ? (putValueByTicker[ticker] ?? 0) : 0,
                };
            });
        }

        const prevTotal = diff?.from_total_usd ?? null;

        res.json({
            meta: {
                cik:            raw.cik,
                fund:           raw.fund,
                filing_date:    raw.filing_date,
                period:         raw.period_of_report,
                accession:      raw.accession,
                aum_usd:        raw.total_value_usd,
                aum_prev_usd:   prevTotal,
                position_count: raw.position_count,
                prev_period:    prev?.period_of_report ?? null,
            },
            holdings: enrichedHoldings,
            married_put_tickers: marriedPutTickers,
            diff: diff ? {
                new_positions:    enrichDiff(diff.new_positions),
                closed_positions: enrichDiff(diff.closed_positions),
                increased:        enrichDiff(diff.increased),
                decreased:        enrichDiff(diff.decreased),
            } : null,
        });
    } catch (e: any) {
        res.status(500).json({ error: e.message });
    }
});

export default router;
