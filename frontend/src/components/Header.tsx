import { TrendingUp } from 'lucide-react';

const Header = () => {
  return (
    <header className="bg-primary text-primary-foreground p-4">
      <div className="container mx-auto flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <TrendingUp className="h-8 w-8" />
          Questrade Portfolio Viewer
        </h1>
      </div>
    </header>
  );
};

export default Header;