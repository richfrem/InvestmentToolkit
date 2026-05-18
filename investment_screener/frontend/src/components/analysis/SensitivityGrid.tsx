import { useMemo } from 'react';

interface SensitivityGridProps {
    peRatio: number;
    growthRate: number;
    stockPrice: number;
    calculateYear5Price: (g: number, pe: number) => number;
    calculatePresentValue: (g: number, pe: number) => number;
}

export function SensitivityGrid({ peRatio, growthRate, stockPrice, calculateYear5Price, calculatePresentValue }: SensitivityGridProps) {
    const currentPe = Math.max(5, Math.round(peRatio / 5) * 5);
    const currentGrowth = Math.round(growthRate / 5) * 5;

    const peRange = useMemo(() =>
        [currentPe - 10, currentPe - 5, currentPe, currentPe + 5, currentPe + 10].filter(p => p > 0),
        [currentPe]
    );

    const growthRange = useMemo(() =>
        [currentGrowth - 10, currentGrowth - 5, currentGrowth, currentGrowth + 5, currentGrowth + 10],
        [currentGrowth]
    );

    return (
        <div className="h-full flex flex-col">
            <div className="flex-1 overflow-auto custom-scrollbar">
                <table className="w-full text-[9px] border-collapse min-w-[280px]">
                    <thead>
                        <tr>
                            <th className="p-1 text-slate-500 font-medium text-left border-b border-slate-800">G \ PE</th>
                            {peRange.map(pe => (
                                <th key={pe} className={`p-1 border-b border-slate-800 text-center transition-colors duration-300 ${pe === currentPe ? 'text-white font-bold bg-purple-500/20' : 'text-slate-600'}`}>
                                    {pe}x
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {growthRange.map(g => (
                            <tr key={g} className="hover:bg-slate-800/30 transition-colors">
                                <td className={`p-1 font-bold border-r border-slate-800/50 ${g === currentGrowth ? 'text-primary' : 'text-slate-500'}`}>
                                    {g}%
                                </td>
                                {peRange.map(pe => {
                                    const y5Price = calculateYear5Price(g, pe);
                                    const pv = calculatePresentValue(g, pe);
                                    
                                    // Upside based on Present Value (Fair Value vs Current Price)
                                    const upside = stockPrice > 0 ? ((pv - stockPrice) / stockPrice) * 100 : 0;

                                    let colorClass = 'text-slate-600';
                                    if (upside > 50) colorClass = 'bg-green-500/20 text-green-400 font-bold';
                                    else if (upside > 20) colorClass = 'bg-green-500/10 text-green-500';
                                    else if (upside > 0) colorClass = 'text-green-600';
                                    else if (upside > -20) colorClass = 'text-red-400';
                                    else colorClass = 'bg-red-500/10 text-red-500 font-bold';

                                    if (g === currentGrowth && pe === currentPe) {
                                        colorClass += ' ring-1 ring-primary relative z-10';
                                    }

                                    return (
                                        <td key={pe} className={`p-1 text-right rounded-sm ${colorClass} group/cell relative`}>
                                            <div className="flex flex-col items-end">
                                                <span className="font-bold">${Math.round(y5Price)}</span>
                                                <span className="text-[7px] opacity-40 group-hover/cell:opacity-100 transition-opacity">PV: ${Math.round(pv)}</span>
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="mt-2 text-[8px] text-slate-500 flex justify-between italic">
                <span>Primary: 5Y Target Price</span>
                <span>Sub: Fair Value (Discounted)</span>
            </div>
        </div>
    );
}
