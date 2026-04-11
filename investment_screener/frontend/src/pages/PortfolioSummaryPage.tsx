import { useState, useEffect } from 'react';
import { fetchPortfolioSummary, type PortfolioSummary } from '../services/api';
import PortfolioSummaryCards from '../components/PortfolioSummaryCards';
import PortfolioBreakdown from '../components/PortfolioBreakdown';

export default function PortfolioSummaryPage() {
    const [data, setData] = useState<PortfolioSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const load = async () => {
            try {
                const summary = await fetchPortfolioSummary();
                setData(summary);
            } catch (err: any) {
                setError(err.message || 'Failed to load portfolio summary');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    if (loading) {
        return (
            <div className="p-6 h-full flex items-center justify-center">
                <div className="text-slate-500 text-sm">Loading portfolio summary...</div>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="p-6 h-full flex items-center justify-center">
                <div className="text-red-400 text-sm">{error || 'No data available'}</div>
            </div>
        );
    }

    return (
        <div className="p-6 h-full space-y-6">
            <div>
                <h1 className="text-xl font-bold text-white mb-1">Portfolio Summary</h1>
                <p className="text-sm text-slate-500">
                    YTD performance and total value across all accounts
                </p>
            </div>
            <PortfolioSummaryCards data={data} />
            <PortfolioBreakdown data={data} />
        </div>
    );
}
