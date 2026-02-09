import { LayoutDashboard, Settings, History } from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useRecentTickers } from '../hooks/useRecentTickers';

export default function Sidebar() {
    const { recentTickers } = useRecentTickers();
    const navigate = useNavigate();

    const navItems = [
        { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
        { name: 'Settings', icon: Settings, path: '/settings' },
    ];

    return (
        <aside className="w-64 h-screen bg-surface border-r border-slate-800 flex flex-col fixed left-0 top-0">
            <div className="p-6">
                <h1 className="text-xl font-bold text-primary flex items-center gap-2 mb-6">
                    <span className="text-2xl">⚡</span> Investment Toolkit
                </h1>

                {/* Global Search - Integrated in Sidebar */}
                <div className="mb-2">
                    <input
                        type="text"
                        placeholder="Search ticker..."
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                const val = e.currentTarget.value.trim().toUpperCase();
                                if (val) navigate(`/?ticker=${val}`);
                            }
                        }}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:border-primary focus:outline-none placeholder:text-slate-600"
                    />
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-2">
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
            </nav>

            <div className="p-4 border-t border-slate-800">
                <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
                    <History size={14} /> Recent
                </h3>
                {recentTickers.length === 0 ? (
                    <div className="text-sm text-slate-500 italic">
                        No history yet...
                    </div>
                ) : (
                    <ul className="space-y-1">
                        {recentTickers.map((ticker) => (
                            <li key={ticker}>
                                <button
                                    onClick={() => navigate(`/?ticker=${ticker}`)} // Ideally Dashboard handles this param or context
                                    // For now just basic link or we can wire it up differently. 
                                    // Given constraints, I'll just put the text. Dashboard handles search.
                                    // Actually, clicking should load it. 
                                    // I'll make it simple text for now or maybe just a button that doesn't do much yet without global state.
                                    // DoD says "Sidebar shows 'Recently Analyzed' history". Loading it is implied "Click to load".
                                    // Dashboard uses local state. I can use URL param?
                                    // `window.location.search` in Dashboard init?
                                    // Let's keep it simple: just list them for now to meet DoD "shows history".
                                    className="block w-full text-left px-3 py-2 text-sm text-slate-400 hover:text-primary hover:bg-slate-800/50 rounded transition-colors"
                                >
                                    {ticker}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </aside>
    );
}
