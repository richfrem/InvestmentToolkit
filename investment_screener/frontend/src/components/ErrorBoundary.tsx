/**
 * ErrorBoundary.tsx - Keep one failing screen from blanking the whole app.
 *
 * Purpose:
 *     A rendering error in any component used to unmount the entire React tree, leaving a
 *     blank page with nothing to read. This catches the error below it, keeps everything
 *     outside it (the sidebar) on screen, shows what failed, and offers a reload. It is keyed by
 *     route in MainLayout, so moving to another screen clears the error.
 *
 * Layer: Frontend / Components
 *
 * Usage Examples:
 *     <ErrorBoundary key={location.pathname}><Outlet /></ErrorBoundary>
 *
 * Key Functions (Index):
 *     - ErrorBoundary: class component with getDerivedStateFromError / componentDidCatch
 *
 * Key Input Dependencies:
 *     - none
 *
 * Key Output Dependencies:
 *     - layouts/MainLayout
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { error: null };

    static getDerivedStateFromError(error: Error): State {
        return { error };
    }

    componentDidCatch(error: Error, info: ErrorInfo): void {
        console.error('Screen crashed:', error, info.componentStack);
    }

    render(): ReactNode {
        const { error } = this.state;
        if (!error) return this.props.children;
        return (
            <div role="alert" className="m-4 rounded-lg border border-red-500/40 bg-red-900/20 p-5 text-sm text-red-200">
                <div className="mb-1 text-base font-bold text-red-100">Something went wrong on this screen</div>
                <p className="mb-3 font-mono text-xs text-red-300">{error.message}</p>
                <p className="mb-3 text-xs text-red-200/80">
                    If you just updated the app, restart the backend (it may still be running the old code), then reload.
                </p>
                <button type="button" onClick={() => window.location.reload()}
                    className="rounded bg-red-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-red-500">Reload</button>
            </div>
        );
    }
}
