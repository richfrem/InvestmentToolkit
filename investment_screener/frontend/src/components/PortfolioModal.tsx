/**
 * PortfolioModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Modal for viewing and potentially managing portfolio holdings.
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <PortfolioModal isOpen={true} onClose={() => {}} />
 *
 * Key Functions:
 *     - savePortfolio() - Persists updated portfolio items to both localStorage and the backend API
 *     - handleAdd() - Validates and adds a new ticker/share count to the portfolio list
 *     - handleUpdateShares() - Updates the share quantity for an existing position and triggers a save
 */
import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';

interface PortfolioItem {
    symbol: string;
    shares: number;
    [key: string]: any; // Allow other fields like sector, industry
}

interface PortfolioModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const PortfolioModal: React.FC<PortfolioModalProps> = ({ isOpen, onClose }) => {
    const [items, setItems] = useState<PortfolioItem[]>([]);
    const [newSymbol, setNewSymbol] = useState('');
    const [newShares, setNewShares] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            // Load from localStorage (synced with backend on save)
            const saved = localStorage.getItem('portfolio_items');
            if (saved) {
                setItems(JSON.parse(saved));
            }
        }
    }, [isOpen]);

    const savePortfolio = async (updatedItems: PortfolioItem[]) => {
        setSaving(true);
        try {
            // Save to localStorage for frontend state
            localStorage.setItem('portfolio_items', JSON.stringify(updatedItems));

            // Persist to backend (writes portfolio.json)
            const response = await fetch('/api/portfolio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: updatedItems })
            });
            if (!response.ok) {
                console.error('Failed to save portfolio to backend');
            }
        } catch (error) {
            console.error('Failed to save portfolio:', error);
        } finally {
            setSaving(false);
        }
    };

    const handleAdd = () => {
        const sym = newSymbol.trim().toUpperCase();
        const shares = parseFloat(newShares) || 0;
        if (sym && shares > 0 && !items.find(i => i.symbol === sym)) {
            const updated = [...items, { symbol: sym, shares }];
            setItems(updated);
            savePortfolio(updated);
            setNewSymbol('');
            setNewShares('');
        }
    };

    const handleRemove = (symbol: string) => {
        const updated = items.filter(i => i.symbol !== symbol);
        setItems(updated);
        savePortfolio(updated);
    };

    const handleUpdateShares = (symbol: string, shares: number) => {
        const updated = items.map(i =>
            i.symbol === symbol ? { ...i, shares } : i
        );
        setItems(updated);
        savePortfolio(updated);
    };

    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999]">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col shadow-2xl">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold text-amber-400">Manage Portfolio</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Add new position */}
                <div className="flex gap-2 mb-4">
                    <input
                        type="text"
                        value={newSymbol}
                        onChange={(e) => setNewSymbol(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
                        placeholder="Ticker..."
                        className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                    />
                    <input
                        type="number"
                        step="any"
                        value={newShares}
                        onChange={(e) => setNewShares(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
                        placeholder="Shares"
                        className="w-24 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                    />
                    <button
                        onClick={handleAdd}
                        className="bg-amber-500 hover:bg-amber-600 text-black font-semibold px-4 py-2 rounded-lg"
                    >
                        Add
                    </button>
                </div>

                {/* Position list */}
                <div className="flex-1 overflow-y-auto pr-2">
                    <div className="text-sm text-gray-400 mb-2">
                        {items.length} positions
                        {saving && <span className="ml-2 text-amber-400">Saving...</span>}
                    </div>
                    <div className="space-y-2">
                        {items.map((item) => (
                            <div
                                key={item.symbol}
                                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 flex justify-between items-center"
                            >
                                <span className="text-white font-mono text-sm w-16">{item.symbol}</span>
                                <input
                                    type="number"
                                    step="any"
                                    value={item.shares}
                                    onChange={(e) => handleUpdateShares(item.symbol, parseFloat(e.target.value) || 0)}
                                    className="w-20 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm text-center"
                                />
                                <span className="text-gray-400 text-xs">shares</span>
                                <button
                                    onClick={() => handleRemove(item.symbol)}
                                    className="text-red-400 hover:text-red-300 ml-2"
                                >
                                    ×
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Footer */}
                <div className="mt-4 pt-4 border-t border-gray-700 flex justify-end">
                    <button
                        onClick={onClose}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );
};