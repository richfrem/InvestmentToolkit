/**
 * TABriefCard.tsx (React Presentation Component)
 * ===============================================
 *
 * Purpose:
 *     Renders a compact, high-density technical analysis momentum card for a single ticker.
 *     Displays Multi-EMA alignment (21/50/200), RSI (14), ADX trend strength, volume bias,
 *     and snapshot data freshness for the Daily Portfolio Brief.
 *
 * Layer: Frontend / Components / Briefs
 *
 * Usage Examples:
 *     <TABriefCard
 *       ticker="NVDA"
 *       rsi={62.4}
 *       adx={28.1}
 *       volBias={0.72}
 *       emaAlignment="BULLISH"
 *     />
 *
 * Key Functions / Components:
 *     - TABriefCard(props: TABriefCardProps) - Pure presentation component rendering technical cards
 *
 * Key Input Dependencies:
 *     - None (Receives typed props from parent DailyBriefPage)
 */

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface TABriefCardProps {
  ticker: string;
  rsi?: number | null;
  adx?: number | null;
  volBias?: number | null;
  emaAlignment?: 'BULLISH' | 'BEARISH' | 'MIXED' | null;
  stalenessDays?: number | null;
}

export const TABriefCard: React.FC<TABriefCardProps> = ({
  ticker,
  rsi,
  adx,
  volBias,
  emaAlignment = 'MIXED',
  stalenessDays,
}) => {
  const getRsiColor = (val?: number | null) => {
    if (!val) return 'text-slate-400';
    if (val >= 70) return 'text-rose-400';
    if (val <= 30) return 'text-emerald-400';
    return 'text-sky-400';
  };

  const getEmaBadge = (alignment?: string | null) => {
    switch (alignment) {
      case 'BULLISH':
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Bullish EMA (21&gt;50&gt;200)</span>;
      case 'BEARISH':
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-950/80 text-rose-400 border border-rose-800/60 flex items-center gap-1"><TrendingDown className="w-3 h-3" /> Bearish EMA</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-800 text-slate-300 border border-slate-700">Neutral / Consolidating</span>;
    }
  };

  return (
    <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 hover:border-slate-700 transition flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-bold text-sm text-slate-200">{ticker}</span>
        {getEmaBadge(emaAlignment)}
      </div>

      <div className="grid grid-cols-3 gap-2 text-xs text-slate-400 pt-1 border-t border-slate-800/60">
        <div>
          <span className="block text-[10px] text-slate-500 uppercase tracking-wider">RSI (14)</span>
          <span className={`font-semibold ${getRsiColor(rsi)}`}>{rsi ? rsi.toFixed(1) : '--'}</span>
        </div>
        <div>
          <span className="block text-[10px] text-slate-500 uppercase tracking-wider">Trend (ADX)</span>
          <span className="font-semibold text-slate-300">{adx ? `${adx.toFixed(1)}` : '--'}</span>
        </div>
        <div>
          <span className="block text-[10px] text-slate-500 uppercase tracking-wider">Vol Bias</span>
          <span className="font-semibold text-slate-300">{volBias ? `${(volBias * 100).toFixed(0)}%` : '--'}</span>
        </div>
      </div>

      {stalenessDays !== undefined && stalenessDays !== null && stalenessDays > 1 && (
        <span className="text-[10px] text-amber-500/80">Snapshot: {stalenessDays}d ago</span>
      )}
    </div>
  );
};
