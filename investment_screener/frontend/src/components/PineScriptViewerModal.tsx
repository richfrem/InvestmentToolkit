/**
 * PineScriptViewerModal.tsx (React Modal Component)
 * ==================================================
 *
 * Purpose:
 *     Modal dialog for viewing, customizing, and 1-click copying the generated
 *     AI Thesis Pine Script overlay code for TradingView Desktop.
 *
 * Layer: Frontend / Components / Modals
 *
 * Usage Examples:
 *     <PineScriptViewerModal
 *         isOpen={isOpen}
 *         onClose={() => setIsOpen(false)}
 *         symbol="NVDA"
 *         fairValue={445.16}
 *         targetEntry={190.0}
 *         stopLoss={170.0}
 *         action="INITIATE"
 *         breakerStatus="OK"
 *     />
 *
 * Key Functions:
 *     - PineScriptViewerModal() - Interactive modal with copy-to-clipboard and syntax preview
 *
 * Key Input Dependencies:
 *     - None (Receives typed props)
 */

import React, { useState } from 'react';
import { X, Copy, Check, ExternalLink, Code } from 'lucide-react';

interface PineScriptViewerModalProps {
    isOpen: boolean;
    onClose: () => void;
    symbol: string;
    fairValue?: number | null;
    targetEntry?: number | null;
    stopLoss?: number | null;
    action?: string | null;
    breakerStatus?: string | null;
}

export const PineScriptViewerModal: React.FC<PineScriptViewerModalProps> = ({
    isOpen,
    onClose,
    symbol,
    fairValue,
    targetEntry,
    stopLoss,
    action = 'MONITOR',
    breakerStatus = 'OK',
}) => {
    const [copied, setCopied] = useState(false);
    const [mode, setMode] = useState<'universal' | 'preset'>('universal');

    if (!isOpen) return null;

    const fvVal = fairValue && fairValue > 0 ? fairValue.toFixed(2) : '0.0';
    const entryVal = targetEntry && targetEntry > 0 ? targetEntry.toFixed(2) : '0.0';
    const stopVal = stopLoss && stopLoss > 0 ? stopLoss.toFixed(2) : '0.0';
    const actStr = action || 'INITIATE';
    const brkStr = breakerStatus || 'OK';

    const universalPineCode = `//@version=6
// AI Thesis & Valuation Overlay — Universal Multi-Ticker
indicator("AI Thesis & Valuation Overlay", shorttitle="AI Thesis", overlay=true)

// === Universal Inputs ===
fairValue   = input.float(${fvVal}, title="Fair Value (DCF Target)", inline="fv")
targetEntry = input.float(${entryVal}, title="Target Entry Limit", inline="entry")
stopLoss    = input.float(${stopVal}, title="Stop Loss / Breaker", inline="stop")
actionText  = input.string("${actStr}", title="Thesis Action", options=["INITIATE", "ACCUMULATE", "MAINTAIN", "TRIM", "EXIT", "MONITOR"])
breakerText = input.string("${brkStr}", title="Breaker Status", options=["OK", "WARNING", "TRIGGERED"])

// === Plot Valuation Lines ===
plot(fairValue > 0 ? fairValue : na, title="Fair Value", color=color.new(color.green, 20), style=plot.style_linebr, linewidth=2)
plot(targetEntry > 0 ? targetEntry : na, title="Target Entry", color=color.new(color.blue, 20), style=plot.style_linebr, linewidth=2)
plot(stopLoss > 0 ? stopLoss : na, title="Stop Loss", color=color.new(color.red, 20), style=plot.style_linebr, linewidth=2)

// === On-Chart HUD Badge ===
var table hud = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 40), border_color=color.gray, border_width=1)
if barstate.islast
    table.cell(hud, 0, 0, "Ticker", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 0, syminfo.ticker, text_color=color.yellow, text_size=size.small)
    table.cell(hud, 0, 1, "Action", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 1, actionText, text_color=color.green, text_size=size.small)
    table.cell(hud, 0, 2, "Breaker", text_color=color.white, text_size=size.small)
    table.cell(hud, 1, 2, breakerText, text_color=color.aqua, text_size=size.small)
`;

    const presetPineCode = `//@version=6
indicator("AI Thesis Overlay - ${symbol}", overlay=true)

// === Valuation Level Inputs ===
fairValue = input.float(${fvVal}, title='Fair Value', inline='fv')
targetEntry = input.float(${entryVal}, title='Target Entry', inline='entry')
stopLoss = input.float(${stopVal}, title='Stop Loss / Breaker', inline='stop')

// === Plot Lines ===
plot(fairValue > 0 ? fairValue : na, title='Fair Value', color=color.new(color.green, 20), style=plot.style_linebr, linewidth=2)
plot(targetEntry > 0 ? targetEntry : na, title='Target Entry', color=color.new(color.blue, 20), style=plot.style_linebr, linewidth=2)
plot(stopLoss > 0 ? stopLoss : na, title='Stop Loss', color=color.new(color.red, 20), style=plot.style_linebr, linewidth=2)

// === Dashboard Status Badge ===
var table infoTable = table.new(position.top_right, 2, 4, bgcolor=color.new(color.black, 40), border_color=color.gray, border_width=1)
if barstate.islast
    table.cell(infoTable, 0, 0, 'Ticker', text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 0, '${symbol}', text_color=color.yellow, text_size=size.small)
    table.cell(infoTable, 0, 1, 'Action', text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 1, '${actStr}', text_color=color.green, text_size=size.small)
    table.cell(infoTable, 0, 2, 'Breaker', text_color=color.white, text_size=size.small)
    table.cell(infoTable, 1, 2, '${brkStr}', text_color=color.aqua, text_size=size.small)
`;

    const activePineCode = mode === 'universal' ? universalPineCode : presetPineCode;

    const handleCopy = () => {
        navigator.clipboard.writeText(activePineCode);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/80">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
                            <Code className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="font-bold text-lg text-white">TradingView Pine Script Overlay</h3>
                            <p className="text-xs text-slate-400">Live DCF & Target Entry Indicator for <span className="text-primary font-bold">{symbol}</span></p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4 overflow-y-auto">
                    {/* Mode Toggle */}
                    <div className="flex items-center justify-between p-1 bg-slate-950 border border-slate-800 rounded-xl">
                        <button
                            onClick={() => setMode('universal')}
                            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium transition-all ${
                                mode === 'universal'
                                    ? 'bg-primary/20 text-primary border border-primary/30 shadow-sm font-semibold'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            🌐 Universal (All Tickers)
                        </button>
                        <button
                            onClick={() => setMode('preset')}
                            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium transition-all ${
                                mode === 'preset'
                                    ? 'bg-primary/20 text-primary border border-primary/30 shadow-sm font-semibold'
                                    : 'text-slate-400 hover:text-slate-200'
                            }`}
                        >
                            🎯 {symbol} Specific Preset
                        </button>
                    </div>

                    {/* Instructions banner */}
                    <div className="p-3.5 bg-sky-950/40 border border-sky-800/60 rounded-xl text-xs text-sky-200 flex items-start gap-2.5">
                        <ExternalLink className="w-4 h-4 shrink-0 text-sky-400 mt-0.5" />
                        <div>
                            <span className="font-semibold text-white block mb-0.5">
                                {mode === 'universal'
                                    ? 'Save once in TradingView — works dynamically for ANY stock symbol on your chart!'
                                    : `Hardcodes ${symbol} DCF Fair Value and Target Entry directly into the script.`}
                            </span>
                            1. Click <strong className="text-white">Copy Code</strong>.<br />
                            2. In TradingView Desktop, open <strong className="text-white">Pine Editor</strong> at the bottom.<br />
                            3. Paste and click <strong className="text-white">Add to chart</strong> (or Save to library).
                        </div>
                    </div>

                    {/* Code block */}
                    <div className="relative">
                        <pre className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-emerald-400 overflow-x-auto leading-relaxed max-h-[300px]">
                            {activePineCode}
                        </pre>
                        <button
                            onClick={handleCopy}
                            className={`absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md transition-all ${
                                copied
                                    ? 'bg-emerald-600 text-white'
                                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                            }`}
                        >
                            {copied ? (
                                <>
                                    <Check className="w-3.5 h-3.5" /> Copied!
                                </>
                            ) : (
                                <>
                                    <Copy className="w-3.5 h-3.5" /> Copy Code
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-800 bg-slate-900/60">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
                    >
                        Close
                    </button>
                    <button
                        onClick={handleCopy}
                        className="flex items-center gap-2 px-5 py-2 text-sm font-bold text-white bg-primary hover:bg-primary/90 rounded-lg shadow-lg shadow-primary/20 transition"
                    >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copied ? 'Copied to Clipboard' : 'Copy Pine Script'}
                    </button>
                </div>
            </div>
        </div>
    );
};
