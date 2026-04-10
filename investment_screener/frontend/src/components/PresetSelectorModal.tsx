import React, { useEffect, useState } from 'react';
import { X, TrendingUp, BrainCircuit, User, Trash2, Globe, FileText, Star, BookOpen } from 'lucide-react';
import { fetchProjections } from '../services/api';
import { deleteUserPreset, type UserPreset } from '../services/presets';
import { storage } from '../services/storage';
import { DeepDiveModal } from './DeepDiveModal';

interface PresetOption {
    id: string;
    type: 'yahoo' | 'ai' | 'user';
    label: string;
    description: string;
    timestamp: Date;
    data?: UserPreset;
    aiProjection?: any; // Full AI projection for report viewing
    isDefault?: boolean;
}

interface PresetSelectorModalProps {
    symbol: string;
    onLoad: (preset: PresetOption) => void;
    onViewReport?: (aiProjection: any) => void; // New prop for viewing AI reports
    onClose: () => void;
}

export const PresetSelectorModal: React.FC<PresetSelectorModalProps> = ({
    symbol,
    onLoad,
    onViewReport,
    onClose
}) => {
    const [presets, setPresets] = useState<PresetOption[]>([]);
    const [loading, setLoading] = useState(true);
    const [deepDiveFile, setDeepDiveFile] = useState<string | null>(null);

    useEffect(() => {
        loadPresets();
    }, [symbol]);

    const loadPresets = async () => {
        setLoading(true);
        const options: PresetOption[] = [];

        // Fetch user projections first to determine default status
        let userProjections: any[] = [];
        try {
            userProjections = await storage.syncProjections(symbol);
        } catch (err) {
            console.error("Failed to sync projections", err);
        }

        // Determine who is default
        // If NO user projection is marked isDefault, then Yahoo is default.
        const defaultProjection = userProjections.find(p => p.isDefault);
        const isYahooDefault = !defaultProjection;

        // 1. Yahoo Consensus (always available)
        options.push({
            id: 'yahoo',
            type: 'yahoo',
            label: 'Yahoo Consensus',
            description: 'Latest analyst estimates from Yahoo Finance',
            timestamp: new Date(),
            isDefault: isYahooDefault
        });

        // 2. AI Analysis (conditional)
        try {
            const projections = await fetchProjections(symbol);
            const aiProjections = projections?.filter(p => p.source === 'AI_AGENT') || [];

            aiProjections.forEach((aiProjection, index) => {
                if (aiProjection.aiThesis) {
                    const modelName = aiProjection.aiThesis.model || 'Unknown Model';

                    // Check if this AI projection is in our synced list (by ID) and is default
                    // Or if it matches the defaultProjection found above?
                    // AI projections might be in the userProjections list if they were synced local.
                    // Let's check ID match against defaultProjection
                    const isDef = defaultProjection && defaultProjection.id === aiProjection.id;

                    options.push({
                        id: aiProjection.id || `ai-${index}`, // Use real ID if available
                        type: 'ai',
                        label: `AI Analysis (${modelName})`,
                        description: `Fair Value: $${aiProjection.aiThesis.fairValue?.toFixed(2) || 'N/A'}`,
                        timestamp: new Date(aiProjection.updatedAt || aiProjection.savedAt),
                        isDefault: !!isDef,
                        data: {
                            fairValue: aiProjection.aiThesis.fairValue,
                            bearPrice: aiProjection.scenarios?.bear?.scenarioPrice,
                            basePrice: aiProjection.scenarios?.base?.scenarioPrice,
                            bullPrice: aiProjection.scenarios?.bull?.scenarioPrice
                        } as any,
                        aiProjection: aiProjection
                    });
                }
            });
        } catch (error) {
            console.error('Failed to load AI projections:', error);
        }

        // 3. User Saved Presets
        userProjections.filter(p => p.source === 'USER').forEach(p => {
            options.push({
                id: p.id,
                type: 'user',
                label: p.name,
                description: 'Custom Scenario',
                timestamp: new Date(p.updatedAt),
                isDefault: p.isDefault,
                data: {
                    id: p.id,
                    name: p.name,
                    symbol: p.ticker,
                    scenarios: p.scenarios,
                    globalSettings: p.globalSettings,
                    savedAt: p.savedAt
                },
                // If the user projection has an AI Thesis attached, pass it as aiProjection so buttons appear
                aiProjection: p.aiThesis ? {
                    aiThesis: p.aiThesis,
                    scenarios: p.scenarios, // Reuse user scenarios as the "projection"
                    source: 'AI_AGENT', // Fake source for the report viewer if needed
                    ticker: p.ticker,
                    savedAt: p.savedAt
                } : undefined
            });
        });

        setPresets(options);
        setLoading(false);
    };

    const handleLoad = (preset: PresetOption) => {
        onLoad(preset);
    };

    const handleDelete = (presetId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm('Delete this preset?')) {
            deleteUserPreset(presetId);
            loadPresets(); // Refresh list
        }
    };

    const handleSetDefault = async (preset: PresetOption, e: React.MouseEvent) => {
        e.stopPropagation();
        // Allow setting default for ANY type (user, ai, yahoo)
        // For Yahoo, we pass id='yahoo'. For others, their real ID.

        try {
            await storage.toggleDefaultProjection({
                id: preset.id, // 'yahoo' or UUID
                ticker: symbol
            } as any);

            loadPresets(); // Refresh UI
        } catch (err) {
            console.error(err);
            alert("Failed to set default.");
        }
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'yahoo': return <Globe className="text-blue-400" size={20} />;
            case 'ai': return <BrainCircuit className="text-purple-400" size={20} />;
            case 'user': return <User className="text-green-400" size={20} />;
            default: return null;
        }
    };

    const formatDate = (date: Date) => {
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        }).format(date);
    };

    // Shared star button component to keep things DRY
    const StarButton = ({ preset }: { preset: PresetOption }) => (
        <button
            onClick={(e) => handleSetDefault(preset, e)}
            className={`p-1.5 rounded-md transition-colors ${preset.isDefault ? 'text-yellow-400 bg-yellow-400/10' : 'text-slate-500 hover:text-yellow-400 hover:bg-slate-700'}`}
            title={preset.isDefault ? "Current Default" : "Set as Default"}
        >
            <Star size={14} fill={preset.isDefault ? "currentColor" : "none"} />
        </button>
    );

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col shadow-2xl">
                {/* Header */}
                <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between bg-slate-800/50">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <TrendingUp size={24} className="text-indigo-400" />
                        Load Valuation Preset
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                    {loading ? (
                        <div className="text-center py-12 text-slate-400">
                            Loading presets...
                        </div>
                    ) : (
                        <>
                            {/* System Presets */}
                            <div>
                                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <span className="w-1 h-4 bg-blue-500 rounded-full"></span>
                                    System Presets
                                </h3>
                                <div className="space-y-2">
                                    {presets.filter(p => p.type === 'yahoo' || p.type === 'ai').map(preset => (
                                        <div
                                            key={preset.id}
                                            className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-indigo-500/50 transition-all group"
                                        >
                                            <div className="flex items-start justify-between mb-3">
                                                <div className="flex items-start gap-3 flex-1">
                                                    <div className="mt-0.5">{getIcon(preset.type)}</div>
                                                    <div className="flex-1">
                                                        <div className="font-semibold text-white group-hover:text-indigo-300 transition-colors">
                                                            {preset.label}
                                                        </div>
                                                        <div className="text-sm text-slate-400 mt-0.5">
                                                            {preset.description}
                                                        </div>
                                                        <div className="text-xs text-slate-500 mt-1">
                                                            {preset.type === 'yahoo' ? 'Updated: ' : 'Generated: '}
                                                            {formatDate(preset.timestamp)}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <StarButton preset={preset} />

                                                    {onViewReport && preset.aiProjection && (
                                                        <>
                                                            <button
                                                                className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    onViewReport(preset.aiProjection);
                                                                }}
                                                                title="View detailed AI report"
                                                            >
                                                                <FileText size={14} />
                                                                Report
                                                            </button>

                                                            {preset.aiProjection.aiThesis?.researchReport && (
                                                                <button
                                                                    className="px-3 py-2 bg-purple-900/30 hover:bg-purple-800/40 text-purple-300 border border-purple-500/30 hover:border-purple-400/50 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        setDeepDiveFile(preset.aiProjection.aiThesis.researchReport);
                                                                    }}
                                                                    title="Open Deep Dive Research Report"
                                                                >
                                                                    <BookOpen size={14} />
                                                                    Deep Dive
                                                                </button>
                                                            )}
                                                        </>
                                                    )}
                                                    <button
                                                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleLoad(preset);
                                                        }}
                                                    >
                                                        Load
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* User Saved Presets */}
                            {presets.filter(p => p.type === 'user').length > 0 && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                        <span className="w-1 h-4 bg-green-500 rounded-full"></span>
                                        My Saved Presets
                                    </h3>
                                    <div className="space-y-2">
                                        {presets.filter(p => p.type === 'user').map(preset => (
                                            <div
                                                key={preset.id}
                                                className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-green-500/50 transition-all cursor-pointer group"
                                                onClick={() => handleLoad(preset)}
                                            >
                                                <div className="flex items-start justify-between">
                                                    <div className="flex items-start gap-3 flex-1">
                                                        <div className="mt-0.5">{getIcon(preset.type)}</div>
                                                        <div className="flex-1">
                                                            <div className="font-semibold text-white group-hover:text-green-300 transition-colors">
                                                                {preset.label}
                                                            </div>
                                                            <div className="text-sm text-slate-400 mt-0.5">
                                                                {preset.description}
                                                            </div>
                                                            <div className="text-xs text-slate-500 mt-1">
                                                                Saved: {formatDate(preset.timestamp)}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <StarButton preset={preset} />

                                                        {onViewReport && preset.aiProjection && (
                                                            <>
                                                                <button
                                                                    className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        onViewReport(preset.aiProjection);
                                                                    }}
                                                                    title="View detailed AI report"
                                                                >
                                                                    <FileText size={14} />
                                                                    Report
                                                                </button>

                                                                {preset.aiProjection.aiThesis?.researchReport && (
                                                                    <button
                                                                        className="px-3 py-2 bg-purple-900/30 hover:bg-purple-800/40 text-purple-300 border border-purple-500/30 hover:border-purple-400/50 text-sm font-medium rounded-lg transition-colors flex items-center gap-1.5"
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            setDeepDiveFile(preset.aiProjection.aiThesis.researchReport);
                                                                        }}
                                                                        title="Open Deep Dive Research Report"
                                                                    >
                                                                        <BookOpen size={14} />
                                                                        Deep Dive
                                                                    </button>
                                                                )}
                                                            </>
                                                        )}

                                                        <button
                                                            className="p-1.5 text-slate-400 hover:text-red-400 transition-colors hover:bg-red-500/20 rounded-md"
                                                            onClick={(e) => handleDelete(preset.id, e)}
                                                            title="Delete preset"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                        <button
                                                            className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors"
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                handleLoad(preset)
                                                            }}
                                                        >
                                                            Load
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Empty State */}
                            {presets.filter(p => p.type === 'user').length === 0 && (
                                <div className="text-center py-8 text-slate-500 text-sm">
                                    <User size={32} className="mx-auto mb-2 opacity-50" />
                                    No saved presets yet. Modify scenarios and click "Save" to create one.
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
            {/* Deep Dive Modal */}
            <DeepDiveModal
                isOpen={!!deepDiveFile}
                onClose={() => setDeepDiveFile(null)}
                filename={deepDiveFile}
            />
        </div>
    );
};
