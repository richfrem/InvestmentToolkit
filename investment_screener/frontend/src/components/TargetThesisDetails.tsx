import React from 'react';
import { Target, ShieldAlert, TrendingUp, TrendingDown, Info, ShieldCheck } from 'lucide-react';

interface BuyTier {
    tier: number;
    price: number;
    action: string;
    basis?: string;
    status?: string;
}

interface SellTier {
    tier: number;
    price: number;
    action: string;
    trimPct: number;
    basis?: string;
    status?: string;
}

interface StopLoss {
    price: number;
    basis?: string;
    status?: string;
}

interface PriceLevels {
    buyTiers?: BuyTier[];
    sellTiers?: SellTier[];
    stopLoss?: StopLoss;
}

interface TargetHolding {
    ticker: string;
    targetWeight: number;
    role: string;
    conviction: number;
    agentRationale: string;
    priceLevels?: PriceLevels;
}

interface TargetThesisDetailsProps {
    holding: TargetHolding;
    currentPrice?: number;
}

export const TargetThesisDetails: React.FC<TargetThesisDetailsProps> = ({ holding, currentPrice }) => {
    const { targetWeight, conviction, role, agentRationale, priceLevels } = holding;
    const buyTiers = priceLevels?.buyTiers?.filter(t => t.status !== 'inactive') || [];
    const sellTiers = priceLevels?.sellTiers?.filter(t => t.status !== 'inactive') || [];
    const stopLoss = priceLevels?.stopLoss?.status !== 'inactive' ? priceLevels?.stopLoss : null;

    const getRoleLabel = (r: string) => {
        return r.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    };

    return (
        <div className="mb-6 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
            {/* Top decorative accent */}
            <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-500 opacity-60"></div>
            
            {/* Header info */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-800/60">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400 border border-emerald-500/20">
                        <Target size={20} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-white">Target Portfolio Thesis</h3>
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium border border-slate-700">
                                {getRoleLabel(role)}
                            </span>
                        </div>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Thesis Core Parameters</p>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="text-right">
                        <div className="text-xs text-slate-500 font-medium">Target Allocation</div>
                        <div className="text-lg font-black text-emerald-400">{targetWeight}%</div>
                    </div>
                    <div className="h-8 w-px bg-slate-800/80"></div>
                    <div className="text-right">
                        <div className="text-xs text-slate-500 font-medium">Conviction Score</div>
                        <div className="flex items-center justify-end gap-1.5 mt-0.5">
                            <span className="text-base font-black text-white">{conviction}</span>
                            <span className="text-[10px] text-slate-500">/ 10</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Rationale */}
            {agentRationale && (
                <div className="mb-5 bg-slate-900/40 rounded-lg p-3.5 border border-slate-800/50 text-xs text-slate-300 leading-relaxed">
                    <div className="flex items-start gap-2">
                        <Info size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                        <p><strong className="text-white">Strategic Intent:</strong> {agentRationale}</p>
                    </div>
                </div>
            )}

            {/* Price Levels Grid */}
            {priceLevels && (buyTiers.length > 0 || sellTiers.length > 0 || stopLoss) ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Buy Tiers */}
                    <div className="bg-slate-950/40 border border-slate-900 rounded-lg p-3">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                            <TrendingDown size={14} className="text-emerald-400" /> Buy / Accumulate Tiers
                        </h4>
                        <div className="space-y-2.5">
                            {buyTiers.length > 0 ? (
                                buyTiers.map((tier, idx) => {
                                    const isClose = currentPrice && currentPrice <= tier.price && (tier.price - currentPrice) / tier.price <= 0.02;
                                    return (
                                        <div key={idx} className={`p-2.5 rounded border transition-all ${isClose ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-slate-900/30 border-slate-800/60'}`}>
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="text-[10px] font-semibold text-slate-400">Tier {tier.tier}</span>
                                                <span className="text-xs font-black text-emerald-400">${tier.price.toFixed(2)}</span>
                                            </div>
                                            {tier.basis && (
                                                <p className="text-[10px] text-slate-500 leading-tight">{tier.basis}</p>
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[10px] text-slate-500">No active accumulation levels set.</p>
                            )}
                        </div>
                    </div>

                    {/* Sell Tiers */}
                    <div className="bg-slate-950/40 border border-slate-900 rounded-lg p-3">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                            <TrendingUp size={14} className="text-indigo-400" /> Trim / Profit Tiers
                        </h4>
                        <div className="space-y-2.5">
                            {sellTiers.length > 0 ? (
                                sellTiers.map((tier, idx) => {
                                    const isClose = currentPrice && currentPrice >= tier.price;
                                    return (
                                        <div key={idx} className={`p-2.5 rounded border transition-all ${isClose ? 'bg-indigo-500/10 border-indigo-500/30' : 'bg-slate-900/30 border-slate-800/60'}`}>
                                            <div className="flex justify-between items-center mb-1">
                                                <span className="text-[10px] font-semibold text-slate-400">
                                                    Tier {tier.tier} ({tier.trimPct}% trim)
                                                </span>
                                                <span className="text-xs font-black text-indigo-400">${tier.price.toFixed(2)}</span>
                                            </div>
                                            {tier.basis && (
                                                <p className="text-[10px] text-slate-500 leading-tight">{tier.basis}</p>
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="text-[10px] text-slate-500">No active target trim levels set.</p>
                            )}
                        </div>
                    </div>

                    {/* Stop Loss & Safeguards */}
                    <div className="bg-slate-950/40 border border-slate-900 rounded-lg p-3">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                            <ShieldCheck size={14} className="text-rose-400" /> Risk Management
                        </h4>
                        {stopLoss ? (
                            <div className="bg-rose-500/5 border border-rose-500/20 rounded p-3">
                                <div className="flex justify-between items-center mb-1.5">
                                    <span className="text-[10px] font-semibold text-rose-400 flex items-center gap-1">
                                        <ShieldAlert size={10} /> Thesis Breaker (Stop)
                                    </span>
                                    <span className="text-xs font-black text-rose-400">${stopLoss.price.toFixed(2)}</span>
                                </div>
                                {stopLoss.basis && (
                                    <p className="text-[10px] text-slate-500 leading-normal">{stopLoss.basis}</p>
                                )}
                            </div>
                        ) : (
                            <div className="p-3 bg-slate-900/30 border border-slate-800/60 rounded text-center">
                                <p className="text-[10px] text-slate-500">No active stop loss level defined.</p>
                            </div>
                        )}
                    </div>
                </div>
            ) : (
                <div className="py-4 text-center border border-dashed border-slate-800 rounded-lg">
                    <p className="text-xs text-slate-500">No target price levels derived for this position yet.</p>
                </div>
            )}
        </div>
    );
};
