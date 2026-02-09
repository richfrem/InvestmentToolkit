import { useState } from 'react';
import { Settings, History, Briefcase, Grid3X3, BarChart3, Search } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useRecentTickers } from '../hooks/useRecentTickers';
import { PortfolioModal } from './PortfolioModal';

export default function Sidebar() {
    const { recentTickers } = useRecentTickers();
    const navigate = useNavigate();
    const [isPortfolioOpen, setIsPortfolioOpen] = useState(false);

    // Main nav items (excluding Settings)
    const navItems = [
        { name: 'Heatmap', icon: Grid3X3, path: '/' },
        { name: 'Stock Analysis', icon: BarChart3, path: '/analysis' },
    ];

    return (
        <aside className="w-64 h-screen bg-surface border-r border-slate-800 flex flex-col fixed left-0 top-0 z-[40]">
            {/* Header with Logo */}
            <div className="p-6 pb-4">
                <h1 className="text-xl font-bold text-primary flex items-center gap-2">
                    <span className="text-2xl">⚡</span> Investment Toolkit
                </h1>
            </div>

            {/* Search - Prominent at Top */}
            <div className="px-6 pb-4">
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search ticker (e.g. NVDA)"
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                const val = e.currentTarget.value.trim().toUpperCase();
                                if (val) navigate(`/analysis?ticker=${val}`);
                            }
                        }}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white focus:border-primary focus:outline-none placeholder:text-slate-500"
                    />
                </div>
            </div>

            {/* Main Navigation */}
            <nav className="flex-1 px-4 space-y-1">
                {navItems.map((item) => (
                    <NavLink
                        key={item.name}
                        to={item.path}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                                ? 'bg-slate-800 text-primary'
                                : 'text-secondary hover:bg-slate-800 hover:text-slate-200'
                            }`
                        }
                    >
                        <item.icon size={20} />
                        <span className="font-medium">{item.name}</span>
                    </NavLink>
                ))}

                {/* Portfolio Management Button */}
                <button
                    onClick={() => setIsPortfolioOpen(true)}
                    className="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-secondary hover:bg-slate-800 hover:text-slate-200 w-full"
                >
                    <Briefcase size={20} />
                    <span className="font-medium">Portfolio</span>
                </button>
            </nav>

            {/* Recent Tickers */}
            <div className="px-4 py-4 border-t border-slate-800">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3 flex items-center gap-2 px-2">
                    <History size={14} /> Recent
                </h3>
                {recentTickers.length === 0 ? (
                    <div className="text-sm text-slate-500 italic px-2">
                        No history yet...
                    </div>
                ) : (
                    <ul className="space-y-1">
                        {recentTickers.map((ticker) => (
                            <li key={ticker}>
                                <button
                                    onClick={() => navigate(`/analysis?ticker=${ticker}`)}
                                    className="block w-full text-left px-3 py-2 text-sm text-slate-400 hover:text-primary hover:bg-slate-800/50 rounded transition-colors"
                                >
                                    {ticker}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            {/* Settings - Bottom */}
            <div className="px-4 pb-4 border-t border-slate-800 pt-2">
                <NavLink
                    to="/settings"
                    className={({ isActive }) =>
                        `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${isActive
                            ? 'bg-slate-800 text-primary'
                            : 'text-secondary hover:bg-slate-800 hover:text-slate-200'
                        }`
                    }
                >
                    <Settings size={20} />
                    <span className="font-medium">Settings</span>
                </NavLink>
            </div>

            <PortfolioModal isOpen={isPortfolioOpen} onClose={() => setIsPortfolioOpen(false)} />
        </aside>
    );
}
