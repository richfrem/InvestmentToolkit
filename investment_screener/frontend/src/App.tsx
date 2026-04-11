import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Heatmap from './pages/Heatmap';
import PortfolioTablePage from './pages/PortfolioTablePage';
import PortfolioSummaryPage from './pages/PortfolioSummaryPage';

import { HelpModalProvider } from './components/HelpModal';

function App() {
  return (
    <HelpModalProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Heatmap />} />
            <Route path="portfolio-summary" element={<PortfolioSummaryPage />} />
            <Route path="portfolio-table" element={<PortfolioTablePage />} />
            <Route path="analysis" element={<Dashboard />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </HelpModalProvider>
  );
}

export default App;
