import { useState, useEffect } from 'react';
import { TradePrepModal } from './TradePrepModal';

interface TradeButtonsProps {
    ticker: string;
    shares?: number;
    size?: 'sm' | 'md';
    className?: string;
}

/**
 * Always shows both Prepare Buy (green) and Prepare Sell (red) buttons.
 * Disabled when TradingView is not connected. Self-contained: owns its
 * own TV-status check and TradePrepModal state so it can be dropped
 * anywhere without wiring additional props.
 */
export function TradeButtons({ ticker, shares = 1, size = 'md', className = '' }: TradeButtonsProps) {
    const [tvConnected, setTvConnected] = useState(false);
    const [modal, setModal] = useState<{ action: 'buy' | 'sell' } | null>(null);

    useEffect(() => {
        fetch('/api/tv-status')
            .then(r => r.json())
            .then(d => setTvConnected(d.price_source === 'tradingview'))
            .catch(() => {});
    }, []);

    const sm = size === 'sm';
    const cls = sm
        ? 'px-2 py-0.5 text-[10px] font-bold rounded'
        : 'px-3.5 py-1.5 text-xs font-bold rounded-lg';
    const offlineTip = 'TradingView not connected — open TV Desktop with --remote-debugging-port=9222';

    return (
        <>
            <div className={`flex items-center gap-1.5 ${className}`}>
                <button
                    disabled={!tvConnected}
                    onClick={() => setModal({ action: 'buy' })}
                    title={tvConnected ? `Prepare buy order for ${ticker}` : offlineTip}
                    className={`${cls} transition-colors ${
                        tvConnected
                            ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                            : 'bg-slate-800 text-slate-600 border border-slate-700 cursor-not-allowed'
                    }`}
                >
                    {sm ? 'Buy' : 'Prepare Buy'}
                </button>
                <button
                    disabled={!tvConnected}
                    onClick={() => setModal({ action: 'sell' })}
                    title={tvConnected ? `Prepare sell order for ${ticker}` : offlineTip}
                    className={`${cls} transition-colors ${
                        tvConnected
                            ? 'bg-red-700 hover:bg-red-600 text-white'
                            : 'bg-slate-800 text-slate-600 border border-slate-700 cursor-not-allowed'
                    }`}
                >
                    {sm ? 'Sell' : 'Prepare Sell'}
                </button>
                {!tvConnected && !sm && (
                    <span className="text-[10px] text-slate-600 font-medium" title={offlineTip}>
                        TV Offline
                    </span>
                )}
            </div>

            {modal && (
                <TradePrepModal
                    ticker={ticker}
                    initialAction={modal.action}
                    initialShares={shares}
                    onClose={() => setModal(null)}
                />
            )}
        </>
    );
}
