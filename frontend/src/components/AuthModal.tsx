import { Button } from './ui/button';

interface AuthModalProps {
  onClose: () => void;
}

const AuthModal = ({ onClose }: AuthModalProps) => {
  const handleAuth = () => {
    window.open('/api/auth/start', '_blank');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-card p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-semibold mb-4">Authentication Required</h3>
        <p className="mb-4">Click below to authenticate with Questrade.</p>
        <div className="flex gap-2">
          <Button onClick={handleAuth}>Start Auth</Button>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  );
};

export default AuthModal;