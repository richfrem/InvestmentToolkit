/**
 * main.tsx (React Entry Point)
 * =====================================
 *
 * Purpose:
 *     Mounts the React application to the DOM and initializes the global styling layer.
 *
 * Layer: Frontend / Entry
 *
 * Usage Examples:
 *     (Self-executing via Vite)
 *
 * Key Functions:
 *     - createRoot() - Bootstraps the React application into the #root element with StrictMode enabled
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { RecommendationsProvider } from './contexts/RecommendationsContext'
import { PositionRowsProvider } from './components/positions/PositionRowsProvider'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RecommendationsProvider><PositionRowsProvider><App /></PositionRowsProvider></RecommendationsProvider>
  </StrictMode>,
)
