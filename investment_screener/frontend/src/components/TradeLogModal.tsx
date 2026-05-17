import { useState, useEffect } from 'react';
import { X, CheckCircle, Loader2, TrendingUp, TrendingDown } from 'lucide-react';
import { fetchPosition, logTrade, type PositionData, type TradeLogEntry } from '../services/api';
import { TradePrepModal } from './TradePrepModal';

interface TradeLogModalProps {
    ticker: string;
    initialAction?: 'buy' | 'sell';
    onClose: () => void;
}

const ACCOUNTS = ['TFSA', 'RRSP', 'CASH', 'MARGIN'];

function fmt$(n: number | null, digits = 2) {
    if (n == null) return '—';
    return `$${Math.abs(n).toFixed(digits)}`;
}

function fmtPct(n: number | null) {
    if (n == null) return '—';
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}

export function TradeLogModal({ ticker, initialAction = 'buy', onClose }: TradeLogModalProps) {
    const [action, setAction] = useState<'buy' | 'sell'>(initialAction);
    const [shares, setShares] = useState(1);
    const [price, setPrice] = useState('');
    const [account, setAccount] = useState('TFSA');
    const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
    const [notes, setNotes] = useState('');

    const [position, setPosition] = useState<PositionData | null>(null);
    const [posLoading, setPosLoading] = useState(true);

    const [submitting, setSubmitting] = useState(false);
    const [result, setResult] = useState<TradeLogEntry | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [showExecModal, setShowExecModal] = useState(false);

    useEffect(() => {
        fetchPosition(ticker)
            .then(p => {
                setPosition(p);
                if (p.price != null) setPrice(p.price.toFixed(2));
            })
            .catch(() => {})
            .finally(() => setPosLoading(false));
    }, [ticker]);

    const handleSubmit = async () => {
        setSubmitting(true);
        setError(null);
        try {
            const { entry } = await logTrade({
                ticker,
                action,
                shares,
                price: parseFloat(price) || 0,
                account,
                date,
                notes: notes.trim(),
            });
            setResult(entry);
        } catch (e: any) {
            setError(e.message ?? 'Failed to log trade');
        } finally {
            setSubmitting(false);
        }
    };

    const totalCost = shares * (parseFloat(price) || 0);
    const gain = position?.unrealizedGain;
    const gainPct = position?.unrealizedGainPct;
    const gainPositive = gain != null && gain >= 0;

    if (showExecModal) {
        return (
            <TradePrepModal
                ticker={ticker}
                initialAction={action}
                initialShares={shares}
                onClose={onClose}
            />
        );
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <span className="px-2.5 py-0.5 rounded border text-xs font-black uppercase tracking-wider text-slate-300 border-slate-600 bg-slate-800">
                            Log Trade
                        </span>
                        <span className="text-white font-bold text-lg">{ticker}</span>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto">
                    {result ? (
                        /* ── Success ── */
                        <div className="p-6 space-y-4">
                            <div className="flex items-center gap-2">
                                <CheckCircle size={20} className="text-emerald-400" />
                                <span className="text-emerald-400 font-bold text-lg">Trade Logged</span>
                            </div>
                            <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 space-y-2">
                                <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-xs font-black uppercase ${result.action === 'buy' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-red-500/15 text-red-400'}`}>
                                        {result.action}
                                    </span>
                                    <span className="text-white font-mono font-semibold">
                                        {result.shares} {result.ticker} @ ${result.price.toFixed(2)}
                                    </span>
                                </div>
                                <div className="text-slate-400 text-xs">{result.account} · {result.date}</div>
                                <div className="text-slate-300 text-sm font-medium pt-1">
                                    Total: ${result.totalCost.toFixed(2)}
                                </div>
                                {result.notes && <div className="text-slate-500 text-xs italic">{result.notes}</div>}
                            </div>
                        </div>
                    ) : (
                        <div className="p-5 space-y-4">
                            {/* ── Position Summary ── */}
                            <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4">
                                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">Current Position</div>
                                {posLoading ? (
                                    <div className="flex items-center gap-2 text-slate-500 text-xs">
                                        <Loader2 size={11} className="animate-spin" /> Loading...
                                    </div>
                                ) : position && position.shares > 0 ? (
                                    <div className="space-y-1">
                                        {/* Account grid header */}
                                        <div className="grid grid-cols-3 text-[10px] text-slate-600 uppercase tracking-wide pb-1">
                                            <span>Account</span><span className="text-right">Shares</span><span className="text-right">Avg Cost</span>
                                        </div>
                                        {position.accounts.length > 0 ? (
                                            position.accounts.map(({ account: acct, shares: s }) => (
                                                <div key={acct} className="grid grid-cols-3 text-xs">
                                                    <span className="text-slate-400">{acct}</span>
                                                    <span className="text-right text-slate-200 font-mono">{s.toLocaleString()}</span>
                                                    <span className="text-right text-slate-500 font-mono">—</span>
                                                </div>
                                            ))
                                        ) : null}
                                        {/* Total row */}
                                        <div className="grid grid-cols-3 text-xs pt-1.5 border-t border-slate-700/60">
                                            <span className="text-slate-400 font-semibold">Total</span>
                                            <span className="text-right text-white font-mono font-bold">{position.shares.toLocaleString()}</span>
                                            <span className="text-right text-slate-300 font-mono font-semibold">
                                                {position.book_price != null ? `$${position.book_price.toFixed(2)}` : '—'}
                                            </span>
                                        </div>
                                        {/* Market price row */}
                                        <div className="grid grid-cols-3 text-xs pt-1 text-slate-500">
                                            <span>Market</span>
                                            <span className="text-right col-span-2 text-slate-300 font-mono">
                                                {position.price != null ? `$${position.price.toFixed(2)}` : '—'}
                                            </span>
                                        </div>
                                        {/* Gain / Loss bar */}
                                        {gain != null && (
                                            <div className={`flex items-center justify-between rounded-lg border px-3 py-2 mt-1 ${gainPositive ? 'bg-emerald-500/8 border-emerald-500/20' : 'bg-red-500/8 border-red-500/20'}`}>
                                                <span className="text-slate-500 text-[10px] uppercase tracking-wide font-semibold">Unrealized P&amp;L</span>
                                                <div className="flex items-center gap-3">
                                                    <span className={`font-mono font-bold text-xs ${gainPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {gainPositive ? '+' : '−'}${Math.abs(gain).toFixed(2)}
                                                    </span>
                                                    <span className={`font-mono text-[11px] font-semibold px-1.5 py-0.5 rounded ${gainPositive ? 'bg-emerald-500/15 text-emerald-300' : 'bg-red-500/15 text-red-300'}`}>
                                                        {fmtPct(gainPct)}
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="text-xs text-slate-500 italic">No position in {ticker}</div>
                                )}
                            </div>

                            {/* ── Action toggle ── */}
                            <div className="flex rounded-lg overflow-hidden border border-slate-700">
                                <button
                                    onClick={() => setAction('buy')}
                                    className={`flex-1 py-2 text-sm font-bold transition-colors ${action === 'buy' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                                >
                                    Buy
                                </button>
                                <button
                                    onClick={() => setAction('sell')}
                                    className={`flex-1 py-2 text-sm font-bold transition-colors ${action === 'sell' ? 'bg-red-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                                >
                                    Sell
                                </button>
                            </div>

                            {/* ── Form ── */}
                            <div className="space-y-3">
                                <div className="grid grid-cols-2 gap-3">
                                    <label className="flex flex-col gap-1">
                                        <span className="text-xs text-slate-500">Shares</span>
                                        <input
                                            type="number" min={1} value={shares}
                                            onChange={e => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        />
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        <span className="text-xs text-slate-500">Price (USD)</span>
                                        <input
                                            type="number" step="0.01" value={price}
                                            onChange={e => setPrice(e.target.value)}
                                            placeholder="0.00"
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        />
                                    </label>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <label className="flex flex-col gap-1">
                                        <span className="text-xs text-slate-500">Account</span>
                                        <select
                                            value={account} onChange={e => setAccount(e.target.value)}
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        >
                                            {ACCOUNTS.map(a => <option key={a} value={a}>{a}</option>)}
                                        </select>
                                    </label>
                                    <label className="flex flex-col gap-1">
                                        <span className="text-xs text-slate-500">Date</span>
                                        <input
                                            type="date" value={date}
                                            onChange={e => setDate(e.target.value)}
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        />
                                    </label>
                                </div>
                                <label className="flex flex-col gap-1">
                                    <span className="text-xs text-slate-500">Notes (optional)</span>
                                    <input
                                        type="text" value={notes}
                                        onChange={e => setNotes(e.target.value)}
                                        placeholder="e.g. partial position, limit fill at open..."
                                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                                    />
                                </label>
                            </div>

                            {/* Total preview */}
                            {totalCost > 0 && (
                                <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/60 border border-slate-700/50">
                                    <span className="text-slate-400 text-xs">Total {action === 'buy' ? 'cost' : 'proceeds'}</span>
                                    <span className="text-white font-mono font-bold text-sm">${totalCost.toFixed(2)}</span>
                                </div>
                            )}

                            {error && (
                                <div className="text-red-400 text-xs bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">{error}</div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-800 flex items-center justify-between gap-3">
                    {result ? (
                        <button onClick={onClose} className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-bold transition-colors">
                            Done
                        </button>
                    ) : (
                        <>
                            <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={() => setShowExecModal(true)}
                                className="px-3 py-2 rounded-lg text-xs font-bold border border-emerald-700/50 bg-emerald-900/20 hover:bg-emerald-800/30 text-emerald-400 transition-colors"
                                title="Execute this trade directly in TradingView via CDP"
                            >
                                Execute in TV →
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={submitting || !price || parseFloat(price) <= 0}
                                className="flex-1 px-4 py-2 rounded-lg text-sm font-bold transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center gap-2"
                            >
                                {submitting ? <><Loader2 size={14} className="animate-spin" /> Logging...</> : 'Log Trade →'}
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
