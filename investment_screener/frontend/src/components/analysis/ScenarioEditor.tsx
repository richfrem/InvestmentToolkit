import { SliderInput } from './SliderInput';
import { type Scenario } from '../../services/api';

interface ScenarioEditorProps {
    scenario: Scenario & { weight: number };
    onChange: (updates: Partial<Scenario & { weight: number }>) => void;
    title: string;
    totalWeight: number;
    forwardPE?: number;
}

export function ScenarioEditor({ scenario, onChange, title, totalWeight, forwardPE }: ScenarioEditorProps) {
    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center mb-2">
                <h3 className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider">{title} Case</h3>
                <div className={`text-[9px] px-1.5 py-0.5 rounded border ${Math.abs(totalWeight - 1.0) < 0.01 ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse'}`}>
                    Weight: {Math.round(scenario.weight * 100)}%
                </div>
            </div>

            <SliderInput
                label="Growth"
                value={scenario.growthRate}
                setValue={v => onChange({ growthRate: v })}
                min={-50} max={100} unit="%"
                impact="High"
                helpTopic="growthRate"
            />

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
