/**
 * ProjectionsPanel.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Panel for viewing and editing DCF projection inputs and saving them as presets.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <ProjectionsPanel ticker="AAPL" isOpen={true} onClose={() => {}} onLoad={(p) => {}} />
 *
 * Key Functions:
 *     - loadProjections() - Retrieves saved projection scenarios from the local storage service
 *     - handleDelete() - Triggers a confirmation dialog and deletes a specific projection from storage
 *     - onLoad() - Propagates the selected projection back to the parent component (ValuationModeler)
 */
import { useState, useEffect } from 'react';
import { X, Save, Trash2, RotateCcw } from 'lucide-react';
import { storage } from '../services/storage';
import type { Projection } from '../services/api';

interface ProjectionsPanelProps {
    ticker: string;
    isOpen: boolean;
    onClose: () => void;
    onLoad: (projection: Projection) => void;
}

export function ProjectionsPanel({ ticker, isOpen, onClose, onLoad }: ProjectionsPanelProps) {
    const [projections, setProjections] = useState<Projection[]>([]);

    // Reload projections when panel opens or ticker changes
    useEffect(() => {
        if (isOpen) {
            loadProjections();
        }
    }, [isOpen, ticker]);

    const loadProjections = () => {
        setProjections(storage.getProjections(ticker));
    };

    const handleDelete = (id: string) => {
        if (confirm('Are you sure you want to delete this saved projection?')) {
            storage.deleteProjection(ticker, id);
            loadProjections();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Panel */}
            <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-700 shadow-2xl h-full overflow-y-auto transform transition-transform duration-300">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h2 className="text-xl font-display font-bold text-white">My Projections</h2>
                            <p className="text-slate-400 text-sm mt-1">Saved scenarios for {ticker}</p>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {projections.length === 0 ? (
                        <div className="text-center py-12 px-4 border-2 border-dashed border-slate-800 rounded-xl">
                            <div className="w-12 h-12 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Save className="w-6 h-6 text-slate-500" />
                            </div>
                            <h3 className="text-slate-300 font-medium mb-1">No saved projections</h3>
                            <p className="text-slate-500 text-sm">
                                Adjust the valuation sliders and click "Save" to create a new projection.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {projections.map((proj) => (
                                <div
                                    key={proj.id}
                                    className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-indigo-500/50 transition-colors group"
                                >
                                    <div className="flex justify-between items-start mb-3">
                                        <div>
                                            <h3 className="font-medium text-white mb-1">
                                                {proj.name || 'Untitled Projection'}
                                            </h3>
                                            <p className="text-xs text-slate-500">
                                                {new Date(proj.savedAt).toLocaleDateString()} • {new Date(proj.savedAt).toLocaleTimeString()}
                                            </p>
                                        </div>
                                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => handleDelete(proj.id)}
                                                className="p-1.5 hover:bg-red-500/10 text-slate-400 hover:text-red-400 rounded-lg"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-3 gap-2 mb-4">
                                        <div className="bg-slate-900/50 p-2 rounded-lg text-center">
                                            <div className="text-xs text-slate-500 mb-1">Growth (Base)</div>
                                            <div className="text-indigo-400 font-mono">{proj.scenarios.base.growthRate}%</div>
                                        </div>
                                        <div className="bg-slate-900/50 p-2 rounded-lg text-center">
                                            <div className="text-xs text-slate-500 mb-1">Margin (Base)</div>
                                            <div className="text-emerald-400 font-mono">{proj.scenarios.base.netMargin}%</div>
                                        </div>
                                        <div className="bg-slate-900/50 p-2 rounded-lg text-center">
                                            <div className="text-xs text-slate-500 mb-1">Exit P/E (Base)</div>
                                            <div className="text-amber-400 font-mono">{proj.scenarios.base.exitPE}x</div>
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => {
                                            onLoad(proj);
                                            onClose();
                                        }}
                                        className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                                    >
                                        <RotateCcw className="w-4 h-4" />
                                        Load Projection
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
