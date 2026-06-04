import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import MarkdownContent from './MarkdownContent';

interface ThesisViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  thesisId: string | null;
}

export default function ThesisViewModal({ isOpen, onClose, thesisId }: ThesisViewModalProps) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && thesisId) {
      setLoading(true);
      setError(null);
      fetch(`/api/theses/sub-strategies/${thesisId}`)
        .then(res => {
          if (!res.ok) throw new Error('Failed to load thesis');
          return res.json();
        })
        .then(data => {
          setContent(data.content);
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setError(err.message);
          setLoading(false);
        });
    }
  }, [isOpen, thesisId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-center items-center z-[100] p-4 sm:p-6 overflow-y-auto">
      <div className="bg-[#1C1C1E] border border-white/10 rounded-2xl w-full max-w-4xl flex flex-col my-auto shadow-2xl relative">
        <div className="flex justify-between items-center p-4 border-b border-white/5 shrink-0 sticky top-0 bg-[#1C1C1E] rounded-t-2xl z-10">
          <h2 className="text-xl font-bold text-white tracking-tight">Thesis Viewer</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-xl transition-colors group"
          >
            <X className="w-5 h-5 text-gray-400 group-hover:text-white" />
          </button>
        </div>

        <div className="p-6 md:p-8 overflow-y-auto custom-scrollbar" style={{ maxHeight: 'calc(100vh - 120px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
            </div>
          ) : error ? (
            <div className="text-red-400 text-center py-20">{error}</div>
          ) : (
            <div className="prose prose-invert prose-indigo max-w-none prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-p:text-gray-300 prose-li:text-gray-300">
              <MarkdownContent content={content} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
