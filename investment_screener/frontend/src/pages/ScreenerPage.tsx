import ScreenerTable from '../components/ScreenerTable';

export default function ScreenerPage() {
    return (
        <div className="p-6 h-full flex flex-col">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-white mb-2">AI Analysis Screener</h1>
                <p className="text-slate-400 text-sm">
                    Aggregated intelligence from all deep-dive agent analyses.
                </p>
            </div>
            <div className="flex-1 min-h-0">
                <ScreenerTable />
            </div>
        </div>
    );
}
