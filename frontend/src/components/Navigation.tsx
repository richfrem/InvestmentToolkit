interface NavigationProps {
  onViewChange: (view: string) => void;
}

const Navigation = ({ onViewChange }: NavigationProps) => {
  return (
    <nav className="bg-muted p-2">
      <div className="container mx-auto flex gap-4">
        <button
          onClick={() => onViewChange('dashboard')}
          className="px-4 py-2 rounded hover:bg-accent"
        >
          Dashboard
        </button>
      </div>
    </nav>
  );
};

export default Navigation;