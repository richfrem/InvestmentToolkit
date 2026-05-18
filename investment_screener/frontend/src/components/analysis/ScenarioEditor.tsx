import { SliderInput } from './SliderInput';
import { type Scenario } from '../../services/api';
import { type ComputedScenario } from '../../utils/valuationMath';

interface ScenarioEditorProps {
    scenario: Scenario & { weight: number };
    computed?: ComputedScenario;
    onChange: (updates: Partial<Scenario & { weight: number }>) => void;
    title: string;
    totalWeight: number;
    forwardPE?: number;
    baseMetrics?: {
        revenue: number;
        shares: number;
    };
}

export function ScenarioEditor({ scenario, computed, onChange, title, totalWeight, forwardPE, baseMetrics }: ScenarioEditorProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center mb-2">
                <h3 className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider">{title} Case</h3>
                <div className={`text-[9px] px-1.5 py-0.5 rounded border ${Math.abs(totalWeight - 1.0) < 0.01 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'}`}>
                    Weight: {Math.round(scenario.weight * 100)}%
                </div>
            </div>

            {/* Quick Result Summary */}
            {computed && (
                <div className="grid grid-cols-3 gap-2 mb-2 bg-slate-900/60 p-2 rounded-lg border border-slate-800/50">
                    <div className="text-center">
                        <div className="text-[7px] text-slate-500 uppercase">Y5 Rev</div>
                        <div className="text-xs font-bold text-white">${(computed.year5Revenue / 1000).toFixed(1)}B</div>
                    </div>
                    <div className="text-center border-x border-slate-800/50">
                        <div className="text-[7px] text-slate-500 uppercase">Y5 EPS</div>
                        <div className="text-xs font-bold text-white">${computed.year5EPS.toFixed(2)}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-[7px] text-slate-500 uppercase">Y5 Price</div>
                        <div className="text-xs font-bold text-indigo-400">${Math.round(computed.year5PriceUndiscounted)}</div>
                    </div>
                </div>
            )}

            {/* Foundation Audit */}
            {baseMetrics && (
                <div className="flex justify-between px-2 mb-4 text-[8px] text-slate-600 font-mono italic">
                    <span>Base Rev: ${(baseMetrics.revenue / 1e9).toFixed(2)}B</span>
                    <span>Base Shares: {(baseMetrics.shares / 1e6).toFixed(0)}M</span>
                </div>
            )}

            <SliderInput
                label="Growth"
                value={scenario.growthRate}
                setValue={v => onChange({ growthRate: v })}
                min={-50} max={100} unit="%"
                impact="High"
                helpTopic="growthRate"
            />
...
            <SliderInput
                label="Margin"
                value={scenario.netMargin}
                setValue={v => onChange({ netMargin: v })}
                min={-20} max={80} unit="%"
                impact="High"
                helpTopic="netMargin"
            />

            <SliderInput
                label="Exit P/E"
                value={scenario.exitPE}
                setValue={v => onChange({ exitPE: v })}
                min={1} max={100} unit="x"
                impact="High"
                helpTopic="exitPE"
                note={forwardPE ? `Fwd: ${forwardPE.toFixed(1)}x` : undefined}
            />

            <SliderInput
                label="Probability"
                value={Math.round(scenario.weight * 100)}
                setValue={v => onChange({ weight: v / 100 })}
                min={0} max={100} unit="%"
                impact="Med"
                helpTopic="probabilityWeight"
            />
            
            <div className="pt-2 border-t border-slate-800/50">
                <SliderInput
                    label="Share Change"
                    value={scenario.shareChange}
                    setValue={v => onChange({ shareChange: v })}
                    min={-10} max={10} unit="%"
                    impact="Med"
                    helpTopic="shareChange"
                    note="(-) Buyback"
                />
                
                <SliderInput
                    label="Qual. Mult."
                    value={scenario.qualityMultiplier}
                    setValue={v => onChange({ qualityMultiplier: v })}
                    min={0.5} max={2.0} step={0.05} unit="x"
                    impact="Med"
                    helpTopic="qualityMultiplier"
                    note="Typ: 1.0x"
                />
            </div>
        </div>
    );
}
