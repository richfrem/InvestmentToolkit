import { useState, lazy, Suspense } from "react";
import { TrendingUp } from "lucide-react";
import { Toaster } from 'sonner';
import { Button } from "./components/ui/button";
import DashboardPage from "./pages/DashboardPage";
import { SymbolPillarAllocationsTable } from "./features/portfolio/components/SymbolPillarAllocationsTable";

const TABS = ["DASHBOARD", "EDIT ALLOCATIONS", "STRATEGY AI"];

// Lazy-load StrategyAIPage to avoid bundling server-only or heavy deps in the main chunk
const StrategyAIPage = lazy(() => import('./pages/StrategyAIPage'));

export default function ModernApp() {
  const [activeTab, setActiveTab] = useState("DASHBOARD");

  const renderContent = () => {
    switch (activeTab) {
      case "DASHBOARD":
        return <DashboardPage />;
      case "EDIT ALLOCATIONS":
        return <SymbolPillarAllocationsTable />;
      case "STRATEGY AI":
        return (
          <Suspense fallback={<div>Loading Strategy AI...</div>}>
            <StrategyAIPage />
          </Suspense>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center">
          <div className="mr-4 flex">
            <a className="mr-6 flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              <span className="font-bold">Investment Toolkit</span>
            </a>
            <nav className="flex items-center space-x-2 bg-transparent px-1 py-0">
              {TABS.map((tab) => (
                <Button
                  key={tab}
                  variant={activeTab === tab ? "outline" : "ghost"}
                  onClick={() => setActiveTab(tab)}
                  className={`h-8 px-3 text-sm font-medium rounded-md ${activeTab === tab ? 'bg-muted/60 text-foreground' : 'text-muted-foreground'}`}
                >
                  {tab}
                </Button>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto p-4 md:p-6">{renderContent()}</main>
      <Toaster position="top-right" closeButton />
    </div>
  );
}
