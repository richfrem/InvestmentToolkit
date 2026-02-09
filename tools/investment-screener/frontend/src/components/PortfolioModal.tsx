import { useState, useEffect } from 'react';
import portfolioData from '../data/portfolio.json';

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

    useEffect(() => {
        // Load from localStorage or fall back to JSON file
        const saved = localStorage.getItem('portfolio_items');
        if (saved) {
            setItems(JSON.parse(saved));
        } else {
            setItems(portfolioData as PortfolioItem[]);
        }
    }, [isOpen]);

    const saveToBackend = async (updatedItems: PortfolioItem[]) => {
        try {
            await fetch('http://localhost:3001/api/portfolio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: updatedItems })
            });
        } catch (error) {
            console.error('Failed to save portfolio:', error);
        }
    };

    const handleAdd = () => {
        const sym = newSymbol.trim().toUpperCase();
        const shares = parseInt(newShares) || 0;
        if (sym && shares > 0 && !items.find(i => i.symbol === sym)) {
            const updated = [...items, { symbol: sym, shares }];
            setItems(updated);
            localStorage.setItem('portfolio_items', JSON.stringify(updated));
            saveToBackend(updated);
            setNewSymbol('');
            setNewShares('');
        }
    };

    const handleRemove = (symbol: string) => {
        const updated = items.filter(i => i.symbol !== symbol);
        setItems(updated);
        localStorage.setItem('portfolio_items', JSON.stringify(updated));
        saveToBackend(updated);
    };

    const handleUpdateShares = (symbol: string, shares: number) => {
        const updated = items.map(i =>
            i.symbol === symbol ? { ...i, shares } : i
        );
        setItems(updated);
        localStorage.setItem('portfolio_items', JSON.stringify(updated));
        saveToBackend(updated);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleAdd();
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black flex items-center justify-center z-50">
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
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
                        onKeyPress={handleKeyPress}
                        placeholder="Ticker..."
                        className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:border-amber-500 focus:outline-none"
                    />
                    <input
                        type="number"
                        value={newShares}
                        onChange={(e) => setNewShares(e.target.value)}
                        onKeyPress={handleKeyPress}
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
                <div className="flex-1 overflow-y-auto">
                    <div className="text-sm text-gray-400 mb-2">{items.length} positions</div>
                    <div className="space-y-2">
                        {items.map((item) => (
                            <div
                                key={item.symbol}
                                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 flex justify-between items-center"
                            >
                                <span className="text-white font-mono text-sm w-16">{item.symbol}</span>
                                <input
                                    type="number"
                                    value={item.shares}
                                    onChange={(e) => handleUpdateShares(item.symbol, parseInt(e.target.value) || 0)}
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
        </div>
    );
};
