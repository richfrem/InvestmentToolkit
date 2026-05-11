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
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

export default function MainLayout() {
    return (
        <div className="min-h-screen bg-background text-text flex">
            {/* Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <main className="flex-1 ml-64 p-8 overflow-y-auto">
                {/* Minimal Header (optional, usually title per page) */}

                <Outlet />
            </main>
        </div>
    );
}
