/**
 * MainLayout.tsx (React Layout)
 * =====================================
 *
 * Purpose:
 *     The primary structural shell of the application, providing a persistent sidebar and main content area.
 *
 * Layer: Frontend / Layouts
 *
 * Usage Examples:
 *     <Route element={<MainLayout />}> ... </Route>
 *
 * Key Functions:
 *     - MainLayout() - Root structural component that wraps child routes (via Outlet) with the application's global navigation
 */
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '../components/ErrorBoundary';
import Sidebar from '../components/Sidebar';
import { usePrivacy } from '../context/PrivacyContext';

export default function MainLayout() {
    const { isPrivacyMode } = usePrivacy();
    const location = useLocation();

    return (
        <div className={`min-h-screen bg-background text-text flex ${isPrivacyMode ? 'privacy-mode' : ''}`}>
            {/* Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 ml-60 p-8 overflow-y-auto">
                {/* Minimal Header (optional, usually title per page) */}

                <ErrorBoundary key={location.pathname}>
                    <Outlet />
                </ErrorBoundary>
            </main>
        </div>
    );
}
