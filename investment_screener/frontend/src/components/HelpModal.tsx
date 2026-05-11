/**
 * HelpModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Context-aware help system and modal for explaining financial metrics and toolkit features.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <HelpModalProvider>
 *         <HelpTrigger topicId="ruleOf40" />
 *     </HelpModalProvider>
 *
 * Key Functions:
 *     - openHelp() - Sets the active help topic and makes the modal visible
 *     - PECalculator() - Interactive sub-component for dynamic P/E and target price calculations
 *     - HelpTrigger() - A reusable button component (question mark icon) that triggers the help modal
 */
import { createContext, useContext, useState, type ReactNode } from 'react';
import { HelpCircle, ExternalLink, X } from 'lucide-react';
import { helpTopics, type HelpTopic } from './HelpContent';

// Context definition
interface HelpModalContextType {
    openHelp: (topicId: string) => void;
    closeHelp: () => void;
}

const HelpModalContext = createContext<HelpModalContextType | undefined>(undefined);

// Provider Component
export function HelpModalProvider({ children }: { children: ReactNode }) {
    const [activeTopic, setActiveTopic] = useState<HelpTopic | null>(null);
    const [activeTopicId, setActiveTopicId] = useState<string | null>(null);
    const [isOpen, setIsOpen] = useState(false);

    const openHelp = (topicId: string) => {
        const topic = helpTopics[topicId];
        if (topic) {
            setActiveTopic(topic);
            setActiveTopicId(topicId);
            setIsOpen(true);
        } else {
            console.warn(`Help topic not found: ${topicId}`);
        }
    };

    const closeHelp = () => {
        setIsOpen(false);
        setActiveTopic(null);
        setActiveTopicId(null);
    };

    const showCalculator = activeTopicId === 'exitPE' || activeTopicId === 'forwardPE' || activeTopicId === 'epsEstimate';

    return (
        <HelpModalContext.Provider value={{ openHelp, closeHelp }}>
            {children}
            {isOpen && activeTopic && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center p-4" onClick={closeHelp}>
                    <div
                        className="bg-surface border border-slate-700 rounded-xl shadow-2xl max-w-2xl w-full overflow-hidden animate-in fade-in zoom-in duration-200"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Header */}
                        <div className="bg-slate-900/50 p-4 border-b border-slate-800 flex justify-between items-start">
                            <div>
                                <h3 className="text-lg font-bold text-primary flex items-center gap-2">
                                    <HelpCircle size={18} />
                                    {activeTopic.title}
                                </h3>
                                <p className="text-sm text-slate-400 mt-1 leading-snug">{activeTopic.summary}</p>
                            </div>
                            <button onClick={closeHelp} className="text-secondary hover:text-white transition-colors p-1">
                                <X size={20} />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-4">

                            {/* Interactive Calculator for P/E topics */}
                            {showCalculator && <PECalculator />}

                            {/* Explanation */}
                            <div>
                                <h4 className="text-xs font-bold text-secondary uppercase tracking-wider mb-2">Explanation</h4>
                                <div className="text-sm text-slate-300 space-y-2 whitespace-pre-line">
                                    {activeTopic.explanation}
                                </div>
                            </div>

                            {/* Formula */}
                            {activeTopic.formula && (
                                <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                                    <h4 className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Formula</h4>
                                    <code className="text-xs font-mono text-primary block text-center">
                                        {activeTopic.formula}
                                    </code>
                                </div>
                            )}

                            {/* Example */}
                            {activeTopic.example && (
                                <div>
                                    <h4 className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">Example</h4>
                                    <p className="text-sm text-slate-400 italic border-l-2 border-slate-600 pl-3">
                                        {activeTopic.example}
                                    </p>
                                </div>
                            )}

                            {/* Learn More Link */}
                            {activeTopic.learnMoreUrl && (
                                <div className="pt-2">
                                    <a
                                        href={activeTopic.learnMoreUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 transition-colors"
                                    >
                                        Read full definition on Investopedia
                                        <ExternalLink size={10} />
                                    </a>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </HelpModalContext.Provider>
    );
}

// Hook to use the modal
export function useHelpModal() {
    const context = useContext(HelpModalContext);
    if (!context) {
        throw new Error('useHelpModal must be used within a HelpModalProvider');
    }
    return context;
}

// Trigger Component (The ? icon)
export function HelpTrigger({ topicId, size = 14, className = "" }: { topicId: string, size?: number, className?: string }) {
    const { openHelp } = useHelpModal();

    return (
        <button
            type="button"
            onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                openHelp(topicId);
            }}
            className={`text-slate-500 hover:text-primary transition-colors cursor-help inline-flex items-center justify-center ${className}`}
            title="Click for explanation"
        >
            <HelpCircle size={size} />
        </button>
    );
}

// Internal Calculator Component
function PECalculator() {
    const [price, setPrice] = useState(185);
    const [eps, setEps] = useState(7.71); // Default to Yahoo 2027 estimate
    const [targetPE, setTargetPE] = useState(30);

    // Safety check for calculation
    const calculatedPE = eps > 0 ? (price / eps).toFixed(1) : '—';
    const targetPrice = eps * targetPE;
    const percentChange = ((targetPrice - price) / price * 100);
    const isPositive = percentChange >= 0;

    return (
        <div className="bg-primary/10 rounded-lg p-3 border border-primary/30 space-y-3">
            <h4 className="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                Interactive Calculator
            </h4>

            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="text-xs text-secondary block mb-1">Stock Price ($)</label>
                    <input
                        type="number"
                        value={price}
                        onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-right"
                    />
                </div>
                <div>
                    <label className="text-xs text-secondary block mb-1">EPS ($)</label>
                    <input
                        type="number"
                        value={eps}
                        onChange={(e) => setEps(parseFloat(e.target.value) || 0)}
                        className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-sm text-right"
                    />
                </div>
            </div>

            <div className="flex justify-between items-center text-xs pt-1 border-t border-primary/20">
                <span className="text-slate-300">Implied P/E:</span>
                <span className="font-mono font-bold text-white">{calculatedPE}x</span>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-sm border-t border-slate-700 pt-3">
                <span className="text-slate-400">Target: EPS $</span>
                <span className="font-medium">{eps.toFixed(2)}</span>
                <span className="text-slate-400">×</span>
                <input
                    type="number"
                    value={targetPE}
                    onChange={(e) => setTargetPE(parseFloat(e.target.value) || 0)}
                    className="w-14 bg-slate-800 border border-slate-600 rounded px-2 py-1 text-right text-xs"
                />
                <span className="text-slate-400">P/E =</span>
                <span className="font-bold text-lg">${targetPrice.toFixed(0)}</span>
                <span className={`text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                    ({isPositive ? '+' : ''}{percentChange.toFixed(0)}%)
                </span>
            </div>
        </div>
    );
}
