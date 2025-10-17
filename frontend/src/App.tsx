import { useState } from 'react';
import Header from './components/Header';
import Navigation from './components/Navigation';
import Dashboard from './components/Dashboard';
import AuthModal from './components/AuthModal';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [showAuth, setShowAuth] = useState(false);

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard onAuth={() => setShowAuth(true)} />;
      default:
        return <Dashboard onAuth={() => setShowAuth(true)} />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <Navigation onViewChange={setCurrentView} />
      <main className="container mx-auto p-4">
        {renderView()}
      </main>
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

export default App;