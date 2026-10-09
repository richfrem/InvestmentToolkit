import { useState, useEffect } from 'react';
import { Briefcase, Wifi, WifiOff, ExternalLink } from 'lucide-react';

export default function Settings() {
    const [tvStatus, setTvStatus] = useState<'checking' | 'live' | 'offline'>('checking');

    useEffect(() => {
        fetch('/api/tv-status')
            .then(r => r.json())
            .then(d => setTvStatus(d.price_source === 'tradingview' ? 'live' : 'offline'))
            .catch(() => setTvStatus('offline'));
    }, []);

    return (
        <div className="max-w-2xl space-y-6 py-2">
            <h2 className="text-2xl font-bold text-text">Settings</h2>

            {/* ── Connections ─────────────────────────────────────────────── */}
            <section className="bg-surface rounded-xl border border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Connections</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Data sources and broker integrations</p>
                </div>

                <div className="divide-y divide-slate-800/60">
                    {/* TradingView */}
                    <div className="px-6 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${tvStatus === 'live' ? 'bg-emerald-500/10' : 'bg-slate-800'}`}>
                                {tvStatus === 'live'
                                    ? <Wifi size={18} className="text-emerald-400" />
                                    : <WifiOff size={18} className="text-slate-500" />
                                }
                            </div>
                            <div>
                                <div className="text-sm font-semibold text-slate-200">TradingView</div>
                                <div className="text-xs text-slate-500 mt-0.5">
                                    {tvStatus === 'checking' && 'Checking CDP connection…'}
                                    {tvStatus === 'live' && 'Connected via CDP · live prices + order execution'}
                                    {tvStatus === 'offline' && 'Not connected · prices via yfinance, trading disabled'}
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            {tvStatus === 'live' ? (
                                <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                    Live
                                </span>
                            ) : (
                                <span className="px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-500 text-xs font-bold">
                                    Offline
                                </span>
                            )}
                            {tvStatus === 'offline' && (
                                <a
                                    href="https://www.tradingview.com/download/"
                                    target="_blank"
                                    rel="noreferrer"
                                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                                >
                                    <ExternalLink size={12} />
                                    Setup guide
                                </a>
                            )}
                        </div>
                    </div>

                    {tvStatus === 'offline' && (
                        <div className="px-6 py-3 bg-slate-900/40">
                            <p className="text-xs text-slate-500 leading-relaxed">
                                Launch TradingView Desktop with remote debugging enabled:
                                <code className="ml-1 px-1.5 py-0.5 bg-slate-800 rounded text-slate-300 font-mono text-[11px]">
                                    --remote-debugging-port=9222
                                </code>
                            </p>
                        </div>
                    )}
                </div>
            </section>

            {/* ── Advanced ────────────────────────────────────────────────── */}
            {/* ── Positions ───────────────────────────────────────────────── */}
            <section className="bg-surface rounded-xl border border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Positions</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Where your holdings come from</p>
                </div>
                <div className="px-6 py-4 flex items-start gap-3">
                    <Briefcase size={17} className="text-slate-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-slate-400 leading-relaxed">
                        Holdings, cash and executed trades are loaded from your broker and stored in <code className="text-slate-300">domain_model.sqlite</code>.
                        There is no manual editor: run <strong className="text-slate-200">/tv-portfolio-sync</strong> (TradingView), or{' '}
                        <strong className="text-slate-200">/questrade-sync-portfolio</strong> if you use Questrade, to update them.
                    </p>
                </div>
            </section>
        </div>
    );
}
