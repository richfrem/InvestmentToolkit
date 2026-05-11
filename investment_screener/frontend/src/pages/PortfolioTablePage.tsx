/**
 * PortfolioTablePage.tsx (React Page)
 * =====================================
 *
 * Purpose:
 *     Page wrapper for the granular Portfolio Table, providing a detailed view of individual holdings and positions.
 *
 * Layer: Frontend / Pages
 *
 * Usage Examples:
 *     <PortfolioTablePage />
 *
 * Key Functions:
 *     - PortfolioTablePage() - Functional component that provides the layout container for the PortfolioTable component
 */
import PortfolioTable from '../components/PortfolioTable';

export default function PortfolioTablePage() {
    return (
        <div className="p-6 h-full">
            <PortfolioTable />
        </div>
    );
}
