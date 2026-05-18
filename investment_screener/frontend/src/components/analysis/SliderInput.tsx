import { HelpTrigger } from '../HelpModal';

interface SliderInputProps {
    label: string;
    value: number;
    setValue: (v: number) => void;
    min: number;
    max: number;
    unit?: string;
    step?: number;
    note?: string;
    helpTopic?: string;
    warningThreshold?: number | null;
    impact?: 'High' | 'Med' | 'Low';
}

export function SliderInput({ label, value, setValue, min, max, unit = '', step = 1, note = '', helpTopic = '', warningThreshold = null, impact = 'Low' }: SliderInputProps) {
    const isWarning = warningThreshold !== null && value < warningThreshold;
    const impactColor = impact === 'High' ? 'bg-purple-500' : impact === 'Med' ? 'bg-blue-400' : 'bg-slate-600';

    return (
        <div className="mb-1.5 group">
            <div className="flex justify-between items-center mb-1">
                <div className="flex items-center gap-2">
                    <div className={`w-1 h-3 rounded-full ${impactColor}`} title={`${impact} Impact on Valuation`}></div>
                    <label className={`text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${isWarning ? 'text-red-400' : 'text-slate-300 group-hover:text-white transition-colors'}`}>
                        {label}
                    </label>
                    {helpTopic && (
                        <HelpTrigger topicId={helpTopic} className="opacity-30 hover:opacity-100 transition-opacity" size={12} />
                    )}
                </div>
                <div className="flex items-baseline gap-2">
                    {note && <span className="text-[9px] text-slate-600 font-medium">{note}</span>}
                    <div className={`flex items-center rounded px-2 py-0.5 border ${isWarning ? 'bg-red-500/10 border-red-500/50' : 'bg-slate-800 border-slate-700 group-hover:border-slate-500 transition-colors'}`}>
                        <input
                            type="number"
                            value={value}
                            step={step}
                            onChange={(e) => setValue(Number(e.target.value))}
                            className={`w-12 bg-transparent text-right text-xs font-bold focus:outline-none ${isWarning ? 'text-red-400' : 'text-white'}`}
                        />
                        <span className="text-[10px] text-slate-500 ml-0.5">{unit}</span>
                    </div>
                </div>
            </div>

            <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={value}
                onChange={(e) => setValue(Number(e.target.value))}
                style={{
                    background: `linear-gradient(to right, ${isWarning ? '#ef4444' : '#6366f1'} 0%, ${isWarning ? '#ef4444' : '#6366f1'} ${((value - min) / (max - min)) * 100}%, #1e293b ${((value - min) / (max - min)) * 100}%, #1e293b 100%)`
                }}
                className={`w-full h-1.5 rounded-lg appearance-none cursor-pointer transition-all mt-1 focus:outline-none focus:ring-1 focus:ring-indigo-500/50
                    [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 
                    [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white 
                    [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(0,0,0,0.5)] [&::-webkit-slider-thumb]:mt-[-3px] 
                    ${isWarning ? '[&::-webkit-slider-thumb]:ring-2 [&::-webkit-slider-thumb]:ring-red-500' : ''}`}
            />

            <div className="flex justify-between text-[8px] text-slate-700 mt-0.5 px-0.5">
                <span>{min}</span>
                <span>{max}</span>
            </div>
        </div>
    );
}
