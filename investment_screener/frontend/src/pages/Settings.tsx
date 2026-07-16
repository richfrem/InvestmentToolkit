import { useState, useEffect } from 'react';
import { Briefcase, AlertTriangle, Wifi, WifiOff, ExternalLink } from 'lucide-react';
import { PortfolioModal } from '../components/PortfolioModal';

export default function Settings() {
    const [isPortfolioOpen, setIsPortfolioOpen] = useState(false);
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
            <section className="bg-surface rounded-xl border border-slate-800 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">Advanced</h3>
                    <p className="text-xs text-slate-500 mt-0.5">Bypass options — use only when necessary</p>
                </div>
                <div className="px-6 py-4 space-y-3">
                    <div className="flex items-start gap-2.5 bg-amber-500/5 border border-amber-500/15 rounded-lg p-3">
                        <AlertTriangle size={14} className="text-amber-500/70 mt-0.5 shrink-0" />
                        <p className="text-amber-300/70 text-xs leading-relaxed">
                            Manual portfolio editing bypasses TradingView sync and may cause <code className="text-amber-200/80">portfolio.json</code> to drift from live positions.
                            Prefer <strong className="text-amber-200/80">/tv-portfolio-sync</strong> for routine updates.
                        </p>
                    </div>
                    <button
                        onClick={() => setIsPortfolioOpen(true)}
                        className="flex items-center gap-3 px-4 py-3 rounded-lg border border-slate-700 hover:border-slate-600 hover:bg-slate-800/50 transition-colors text-slate-300 hover:text-white w-full"
                    >
                        <Briefcase size={17} className="text-slate-500" />
                        <div className="text-left">
                            <div className="text-sm font-medium">Manual Portfolio Editor</div>
                            <div className="text-xs text-slate-500">Edit portfolio.json directly</div>
                        </div>
                    </button>
                </div>
            </section>

            <PortfolioModal isOpen={isPortfolioOpen} onClose={() => setIsPortfolioOpen(false)} />
        </div>
    );
}
