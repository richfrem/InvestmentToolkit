import { useState, useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, Loader2, ShieldCheck, Clock, Wifi, TrendingUp } from 'lucide-react';
import { runTradePreflight, runTradeExecute, runTradeSubmit } from '../services/api';

type ModalStep =
    | 'configure'
    | 'running_preflight'
    | 'preflight_result'
    | 'running_execute'
    | 'form_filled'
    | 'submitting'
    | 'done';

interface Provenance {
    portfolioSyncAgeMin: number | null;
    priceSource: string | null;
    tvConnected: boolean;
    dcfAction: string | null;
    dcfFairValue: number | null;
    dcfTimestamp: string | null;
}

interface TradePrepModalProps {
    ticker: string;
    initialAction: 'buy' | 'sell';
    initialShares?: number;
    onClose: () => void;
}

const ORDER_TYPES = ['market', 'limit', 'stop', 'stop_limit'];
const ACCOUNTS = ['tfsa', 'rrsp', 'margin'];

function ProvenanceRow({ icon, label, value, warn }: { icon: React.ReactNode; label: string; value: string; warn?: boolean }) {
    return (
        <div className={`flex items-center gap-2 text-xs ${warn ? 'text-amber-400' : 'text-slate-400'}`}>
            <span className="text-slate-500 shrink-0">{icon}</span>
            <span className="text-slate-500 w-28 shrink-0">{label}</span>
            <span className={`font-medium ${warn ? 'text-amber-400' : 'text-slate-200'}`}>{value}</span>
        </div>
    );
}

function CardRow({ label, value, flag, warn }: { label: string; value: string; flag?: string; warn?: boolean }) {
    return (
        <div className="flex items-center justify-between py-1 border-b border-slate-800/60 last:border-0">
            <span className="text-slate-500 text-xs w-32 shrink-0">{label}</span>
            <span className="text-slate-200 text-xs font-mono font-medium">{value}</span>
            {flag && <span className={`text-[10px] font-bold ml-2 ${warn ? 'text-amber-400' : 'text-emerald-400'}`}>{flag}</span>}
        </div>
    );
}

export function TradePrepModal({ ticker, initialAction, initialShares = 1, onClose }: TradePrepModalProps) {
    const [step, setStep] = useState<ModalStep>('configure');
    const [action] = useState<'buy' | 'sell'>(initialAction);
    const [shares, setShares] = useState(initialShares);
    const [orderType, setOrderType] = useState('market');
    const [limitPrice, setLimitPrice] = useState('');
    const [account, setAccount] = useState('tfsa');

    const [provenance, setProvenance] = useState<Provenance | null>(null);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [preflightCard, setPreflightCard] = useState<Record<string, any> | null>(null);
    const [preflightState, setPreflightState] = useState<string | null>(null);
    const [preflightError, setPreflightError] = useState<string | null>(null);
    const [screenshot, setScreenshot] = useState<string | null>(null);
    const [submitResult, setSubmitResult] = useState<any>(null);
    const [executeError, setExecuteError] = useState<string | null>(null);
    const [submitError, setSubmitError] = useState<string | null>(null);

    // Load provenance on mount
    useEffect(() => {
        const load = async () => {
            const [tvRes, syncRes, projRes] = await Promise.allSettled([
                fetch('/api/tv-status').then(r => r.json()),
                fetch('/api/portfolio/status').then(r => r.json()),
                fetch(`/api/projections/${ticker}`).then(r => r.ok ? r.json() : null),
            ]);

            const tv = tvRes.status === 'fulfilled' ? tvRes.value : null;
            const sync = syncRes.status === 'fulfilled' ? syncRes.value : null;
            const projs = projRes.status === 'fulfilled' ? projRes.value : null;

            let syncAgeMin: number | null = null;
            if (sync?.lastSync) {
                syncAgeMin = Math.round((Date.now() - new Date(sync.lastSync).getTime()) / 60000);
            }

            // Latest AI projection for this ticker
            const aiProjs = Array.isArray(projs) ? projs.filter((p: any) => p.source === 'AI_AGENT') : [];
            const latest = aiProjs.sort((a: any, b: any) =>
                new Date(b.savedAt).getTime() - new Date(a.savedAt).getTime()
            )[0] ?? null;

            setProvenance({
                portfolioSyncAgeMin: syncAgeMin,
                priceSource: tv?.price_source ?? null,
                tvConnected: tv?.price_source === 'tradingview',
                dcfAction: latest?.aiThesis?.action ?? null,
                dcfFairValue: latest?.aiThesis?.fairValue ?? null,
                dcfTimestamp: latest?.savedAt ?? null,
            });
        };
        load().catch(() => {});
    }, [ticker]);

    const runPreflight = async () => {
        setStep('running_preflight');
        setPreflightError(null);
        try {
            const result = await runTradePreflight({
                ticker,
                action,
                shares,
                orderType,
                limitPrice: limitPrice ? parseFloat(limitPrice) : undefined,
                account,
            });
            setSessionId(result.sessionId);
            setPreflightCard(result.card ?? null);
            setPreflightState(result.state);
            if (result.error) setPreflightError(result.error);
            setStep('preflight_result');
        } catch (e: any) {
            setPreflightError(e.message ?? 'Preflight failed');
            setStep('preflight_result');
        }
    };

    const runExecute = async () => {
        if (!sessionId) return;
        setStep('running_execute');
        setExecuteError(null);
        try {
            const result = await runTradeExecute(sessionId);
            setScreenshot(result.screenshot ?? null);
            setStep('form_filled');
        } catch (e: any) {
            setExecuteError(e.message ?? 'Execute failed');
            setStep('preflight_result');
        }
    };

    const runSubmit = async () => {
        if (!sessionId) return;
        setStep('submitting');
        setSubmitError(null);
        try {
            const result = await runTradeSubmit(sessionId);
            setSubmitResult(result.result ?? result);
            setStep('done');
        } catch (e: any) {
            setSubmitError(e.message ?? 'Submit failed');
            setStep('form_filled');
        }
    };

    const actionColor = action === 'buy'
        ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
        : 'text-red-400 border-red-500/30 bg-red-500/10';
    const actionLabel = action === 'buy' ? 'Prepare Buy' : 'Prepare Sell';

    const isBrokerReady = provenance?.tvConnected;
    const isDataStale = provenance?.portfolioSyncAgeMin != null && provenance.portfolioSyncAgeMin > 60;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
                    <div className="flex items-center gap-3">
                        <span className={`px-2.5 py-0.5 rounded border text-xs font-black uppercase tracking-wider ${actionColor}`}>
                            {actionLabel}
                        </span>
                        <span className="text-white font-bold text-lg">{ticker}</span>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors">
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto">

                    {/* Step: Configure */}
                    {step === 'configure' && (
                        <div className="p-5 space-y-5">
                            {/* Data Provenance */}
                            {provenance && (
                                <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4 space-y-2">
                                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">Data Provenance</div>
                                    <ProvenanceRow
                                        icon={<Clock size={12} />}
                                        label="Portfolio sync"
                                        value={provenance.portfolioSyncAgeMin != null ? `${provenance.portfolioSyncAgeMin} min ago` : 'Unknown'}
                                        warn={isDataStale}
                                    />
                                    <ProvenanceRow
                                        icon={<Wifi size={12} />}
                                        label="Price source"
                                        value={provenance.priceSource === 'tradingview' ? 'TradingView Live' : 'yfinance'}
                                    />
                                    <ProvenanceRow
                                        icon={<ShieldCheck size={12} />}
                                        label="Broker"
                                        value={provenance.tvConnected ? 'Connected (Questrade via TV)' : 'Not connected'}
                                        warn={!provenance.tvConnected}
                                    />
                                    {provenance.dcfAction && (
                                        <ProvenanceRow
                                            icon={<TrendingUp size={12} />}
                                            label="DCF signal"
                                            value={`${provenance.dcfAction}${provenance.dcfFairValue ? ` · Fair value: $${provenance.dcfFairValue.toFixed(2)}` : ''}`}
                                        />
                                    )}
                                </div>
                            )}
                            {!provenance && (
                                <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-4 flex items-center gap-2 text-slate-500 text-sm">
                                    <Loader2 size={14} className="animate-spin" /> Loading data provenance...
                                </div>
                            )}

                            {/* Warnings */}
                            {!isBrokerReady && (
                                <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
                                    <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                                    <p className="text-amber-300 text-xs">TradingView is not connected. Open TradingView Desktop with <code className="bg-slate-800 px-1 rounded">--remote-debugging-port=9222</code> and ensure Questrade is connected.</p>
                                </div>
                            )}
                            {isDataStale && (
                                <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
                                    <AlertTriangle size={14} className="text-amber-400 mt-0.5 shrink-0" />
                                    <p className="text-amber-300 text-xs">Portfolio data is stale ({provenance?.portfolioSyncAgeMin} min old). Run <strong>/tv-portfolio-sync</strong> before placing orders.</p>
                                </div>
                            )}

                            {/* Order Form */}
                            <div className="space-y-3">
                                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500">Order Details</div>
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
                                        <span className="text-xs text-slate-500">Order Type</span>
                                        <select
                                            value={orderType} onChange={e => setOrderType(e.target.value)}
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        >
                                            {ORDER_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
                                        </select>
                                    </label>
                                </div>
                                {(orderType === 'limit' || orderType === 'stop_limit') && (
                                    <label className="flex flex-col gap-1">
                                        <span className="text-xs text-slate-500">Limit Price (USD)</span>
                                        <input
                                            type="number" step="0.01" value={limitPrice}
                                            onChange={e => setLimitPrice(e.target.value)}
                                            placeholder="e.g. 142.50"
                                            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                        />
                                    </label>
                                )}
                                <label className="flex flex-col gap-1">
                                    <span className="text-xs text-slate-500">Account</span>
                                    <select
                                        value={account} onChange={e => setAccount(e.target.value)}
                                        className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                                    >
                                        {ACCOUNTS.map(a => <option key={a} value={a}>{a.toUpperCase()}</option>)}
                                    </select>
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Step: Running preflight */}
                    {step === 'running_preflight' && (
                        <div className="p-8 flex flex-col items-center gap-4 text-center">
                            <Loader2 size={32} className="text-indigo-400 animate-spin" />
                            <div>
                                <div className="text-white font-semibold">Running preflight check...</div>
                                <div className="text-slate-500 text-sm mt-1">Checking broker status and buying power via CDP</div>
                            </div>
                        </div>
                    )}

                    {/* Step: Preflight result */}
                    {step === 'preflight_result' && (
                        <div className="p-5 space-y-4">
                            {preflightState === 'PREFLIGHT_PASSED' && preflightCard ? (
                                <>
                                    <div className="flex items-center gap-2">
                                        <CheckCircle size={18} className="text-emerald-400" />
                                        <span className="text-emerald-400 font-bold">Preflight Passed</span>
                                    </div>
                                    <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 space-y-0">
                                        <CardRow label="Via" value="TradingView (Questrade)" />
                                        <CardRow label="Ticker" value={preflightCard.ticker ?? ticker} />
                                        <CardRow label="Action" value={String(preflightCard.action ?? action).toUpperCase()} />
                                        <CardRow label="Shares" value={String(preflightCard.shares ?? shares)} />
                                        <CardRow label="Order Type" value={preflightCard.priceDisplay ?? orderType} />
                                        <CardRow
                                            label="Account"
                                            value={`${preflightCard.accountType ?? account.toUpperCase()} ${preflightCard.accountId ? `(#${preflightCard.accountId})` : ''}`}
                                        />
                                        <CardRow label="Cost Estimate" value={preflightCard.costEstimateDisplay ?? '—'} />
                                        <CardRow
                                            label="Buying Power"
                                            value={preflightCard.buyingPowerDisplay ?? '—'}
                                            flag={preflightCard.coverage?.sufficient ? '✓ Sufficient' : '✗ Insufficient'}
                                            warn={!preflightCard.coverage?.sufficient}
                                        />
                                        {preflightCard.dataFreshnessMinutes != null && (
                                            <CardRow
                                                label="Data Age"
                                                value={`${preflightCard.dataFreshnessMinutes} min`}
                                                flag={preflightCard.dataFreshnessMinutes <= 60 ? '✓ Fresh' : '⚠ Stale'}
                                                warn={preflightCard.dataFreshnessMinutes > 60}
                                            />
                                        )}
                                    </div>
                                    {executeError && (
                                        <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                                            <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
                                            <p className="text-red-300 text-xs">{executeError}</p>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <AlertTriangle size={18} className="text-red-400" />
                                        <span className="text-red-400 font-bold">
                                            {preflightState === 'DATA_STALE_BLOCKED' ? 'Blocked — Stale Data'
                                                : preflightState === 'SIZE_CAP_BLOCKED' ? 'Blocked — Size Cap'
                                                : 'Preflight Failed'}
                                        </span>
                                    </div>
                                    <p className="text-slate-300 text-sm">{preflightError}</p>
                                    {preflightCard?._sizeWarning && (
                                        <p className="text-amber-300 text-xs">{preflightCard._sizeWarning}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step: Running execute */}
                    {step === 'running_execute' && (
                        <div className="p-8 flex flex-col items-center gap-4 text-center">
                            <Loader2 size={32} className="text-indigo-400 animate-spin" />
                            <div>
                                <div className="text-white font-semibold">Opening order dialog in TradingView...</div>
                                <div className="text-slate-500 text-sm mt-1">Filling the form via CDP — this may take 15–30 seconds</div>
                            </div>
                        </div>
                    )}

                    {/* Step: Form filled */}
                    {step === 'form_filled' && (
                        <div className="p-5 space-y-4">
                            <div className="flex items-center gap-2">
                                <CheckCircle size={18} className="text-emerald-400" />
                                <span className="text-emerald-400 font-bold">Order Dialog Filled</span>
                            </div>
                            <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-4 space-y-2">
                                <p className="text-slate-300 text-sm">The TradingView order form has been filled. Review it in the TradingView window before confirming.</p>
                                {screenshot && (
                                    <p className="text-slate-500 text-xs font-mono break-all">Screenshot: {screenshot}</p>
                                )}
                            </div>
                            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3">
                                <p className="text-amber-300 text-xs font-semibold">Clicking "Confirm & Submit" will immediately submit the order through TradingView. This action cannot be undone.</p>
                            </div>
                            {submitError && (
                                <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-xl p-3">
                                    <AlertTriangle size={14} className="text-red-400 mt-0.5 shrink-0" />
                                    <p className="text-red-300 text-xs">{submitError}</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step: Submitting */}
                    {step === 'submitting' && (
                        <div className="p-8 flex flex-col items-center gap-4 text-center">
                            <Loader2 size={32} className="text-indigo-400 animate-spin" />
                            <div>
                                <div className="text-white font-semibold">Submitting order...</div>
                                <div className="text-slate-500 text-sm mt-1">Confirming and syncing portfolio after submission</div>
                            </div>
                        </div>
                    )}

                    {/* Step: Done */}
                    {step === 'done' && (
                        <div className="p-5 space-y-4">
                            <div className="flex items-center gap-2">
                                <CheckCircle size={20} className="text-emerald-400" />
                                <span className="text-emerald-400 font-bold text-lg">Order Submitted</span>
                            </div>
                            <p className="text-slate-300 text-sm">Your order has been submitted via TradingView. Portfolio sync is running in the background.</p>
                            {submitResult?.status && (
                                <div className="bg-slate-800/60 rounded-xl border border-slate-700/50 p-3">
                                    <span className="text-slate-400 text-xs font-mono">{JSON.stringify(submitResult, null, 2)}</span>
                                </div>
                            )}
                        </div>
                    )}

                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-800 flex items-center justify-between gap-3">
                    {step === 'done' ? (
                        <button onClick={onClose} className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-bold transition-colors">
                            Done
                        </button>
                    ) : step === 'configure' ? (
                        <>
                            <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={runPreflight}
                                disabled={!isBrokerReady || !provenance}
                                title={!isBrokerReady ? 'TradingView must be connected to run preflight' : undefined}
                                className="flex-1 px-4 py-2 rounded-lg text-sm font-bold transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white"
                            >
                                Run Preflight →
                            </button>
                        </>
                    ) : step === 'preflight_result' && preflightState === 'PREFLIGHT_PASSED' ? (
                        <>
                            <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={runExecute}
                                className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-bold transition-colors"
                            >
                                Open Order Dialog →
                            </button>
                        </>
                    ) : step === 'preflight_result' ? (
                        <>
                            <button onClick={() => setStep('configure')} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                ← Back
                            </button>
                            <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                Close
                            </button>
                        </>
                    ) : step === 'form_filled' ? (
                        <>
                            <button onClick={onClose} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={runSubmit}
                                className="flex-1 px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg text-sm font-bold transition-colors"
                            >
                                Confirm &amp; Submit →
                            </button>
                        </>
                    ) : (
                        // Loading states: no footer buttons
                        <div className="flex-1" />
                    )}
                </div>
            </div>
        </div>
    );
}
