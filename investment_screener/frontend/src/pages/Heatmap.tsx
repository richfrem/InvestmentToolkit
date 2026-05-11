/**
 * Heatmap.tsx (React Page)
 * =====================================
 *
 * Purpose:
 *     Page wrapper for the Portfolio Heatmap, providing a high-level visual representation of portfolio concentrations and performance.
 *
 * Layer: Frontend / Pages
 *
 * Usage Examples:
 *     <Heatmap />
 *
 * Key Functions:
 *     - Heatmap() - Main render function that provides the layout container for the PortfolioHeatmap component
 */
import PortfolioHeatmap from '../components/PortfolioHeatmap';

export default function Heatmap() {
    return (
        <div className="p-6 h-full">
            <PortfolioHeatmap />
        </div>
    );
}
