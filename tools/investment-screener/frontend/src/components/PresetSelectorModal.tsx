import React, { useEffect, useState } from 'react';
import { X, TrendingUp, BrainCircuit, User, Trash2, Globe } from 'lucide-react';
import { fetchProjections } from '../services/api';
import { loadUserPresets, deleteUserPreset, type UserPreset } from '../services/presets';

interface PresetOption {
    id: string;
    type: 'yahoo' | 'ai' | 'user';
    label: string;
    description: string;
    timestamp: Date;
    data?: UserPreset;
}

interface PresetSelectorModalProps {
    symbol: string;
    onLoad: (preset: PresetOption) => void;
    onClose: () => void;
}

export const PresetSelectorModal: React.FC<PresetSelectorModalProps> = ({
    symbol,
    onLoad,
    onClose
}) => {
    const [presets, setPresets] = useState<PresetOption[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadPresets();
    }, [symbol]);

    const loadPresets = async () => {
        setLoading(true);
        const options: PresetOption[] = [];

        // 1. Yahoo Consensus (always available)
        options.push({
            id: 'yahoo',
            type: 'yahoo',
            label: 'Yahoo Consensus',
            description: 'Latest analyst estimates from Yahoo Finance',
            timestamp: new Date()
        });

        // 2. AI Analysis (conditional - show ALL AI projections, grouped by model)
        try {
            const projections = await fetchProjections(symbol);
            const aiProjections = projections?.filter(p => p.source === 'AI_AGENT') || [];

            aiProjections.forEach((aiProjection, index) => {
                if (aiProjection.aiThesis) {
                    const modelName = aiProjection.aiThesis.model || 'Unknown Model';

                    options.push({
                        id: `ai-${index}`,
                        type: 'ai',
                        label: `AI Analysis (${modelName})`,
                        description: `Fair Value: $${aiProjection.aiThesis.fairValue?.toFixed(2) || 'N/A'}`,
                        timestamp: new Date(aiProjection.updatedAt || aiProjection.savedAt),
                        data: {
                            fairValue: aiProjection.aiThesis.fairValue,
                            bearPrice: aiProjection.scenarios?.bear?.targetPrice,
                            basePrice: aiProjection.scenarios?.base?.targetPrice,
                            bullPrice: aiProjection.scenarios?.bull?.targetPrice
                        } as any
                    });
                }
            });
        } catch (error) {
            console.error('Failed to load AI projections:', error);
        }

        // 3. User Saved Presets
        const userPresets = loadUserPresets(symbol);
        userPresets.forEach(preset => {
            options.push({
                id: preset.id,
                type: 'user',
                label: preset.name,
                description: preset.description || 'Custom scenario',
                timestamp: new Date(preset.savedAt),
                data: preset
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
                                            className="bg-slate-800/50 border border-slate-700 rounded-xl p-4 hover:border-indigo-500/50 transition-all cursor-pointer group"
                                            onClick={() => handleLoad(preset)}
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
                                                <button
                                                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
                                                    onClick={() => handleLoad(preset)}
                                                >
                                                    Load
                                                </button>
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
                                                        <button
                                                            className="p-2 text-slate-400 hover:text-red-400 transition-colors"
                                                            onClick={(e) => handleDelete(preset.id, e)}
                                                            title="Delete preset"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                        <button
                                                            className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors"
                                                            onClick={() => handleLoad(preset)}
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
        </div>
    );
};
