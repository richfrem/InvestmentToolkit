import { useEffect, useState } from 'react';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import axios from 'axios';
// react-markdown is dynamically imported to avoid build-time type issues if not installed

export default function StrategyAIPage() {
  const [thesis, setThesis] = useState('');
  const [prompt, setPrompt] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [MarkdownComponent, setMarkdownComponent] = useState<any>(null);

  useEffect(() => {
    // Try to load Thesis.md from TargetPortfolio
    (async () => {
      try {
        const res = await axios.get('/api/file-content?file=Thesis.md');
        if (res.data && res.data.content) {
          setThesis(res.data.content);
        }
      } catch (err) {
        // ignore
      }
    })();
    // Dynamically import react-markdown if available
    (async () => {
      try {
        const m = await import('react-markdown');
        setMarkdownComponent(() => m.default || m);
      } catch (err) {
        // ignore if not installed
      }
    })();
  }, []);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setAnalysis('');
    try {
      const res = await axios.post('/api/run-analysis', { thesis });
      if (res.data && res.data.analysis) {
        setAnalysis(res.data.analysis);
      } else if (res.data && res.data.error) {
        setError(res.data.error);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'unknown';
      setError('Error running analysis: ' + msg);
      toast.error('Failed to get analysis. ' + (msg || 'Check server logs.'));
    } finally {
      setLoading(false);
    }
  };

  const saveThesis = async () => {
    try {
      await axios.post('/api/save-thesis', { content: thesis });
      toast.success('Thesis saved');
    } catch (err) {
      toast.error('Failed to save thesis');
    }
  };

  const savePrompt = async () => {
    try {
      await axios.post('/api/save-prompt', { content: prompt });
      toast.success('Prompt saved');
    } catch (err) {
      toast.error('Failed to save prompt');
    }
  };

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <Card className="col-span-1 md:col-span-1">
        <CardHeader>
          <CardTitle>Investor Thesis</CardTitle>
        </CardHeader>
        <CardContent>
          <textarea value={thesis} onChange={e => setThesis(e.target.value)} className="w-full h-64 p-2 border rounded-md" />
          <div className="mt-2 flex justify-end space-x-2">
            <Button onClick={saveThesis}>Save Thesis</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="col-span-1 md:col-span-1">
        <CardHeader>
          <CardTitle>Prompt (editable)</CardTitle>
        </CardHeader>
        <CardContent>
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Optional: customize the prompt" className="w-full h-64 p-2 border rounded-md" />
          <div className="mt-2 flex justify-end space-x-2">
            <Button onClick={savePrompt}>Save Prompt</Button>
            <Button onClick={runAnalysis} disabled={loading}>{loading ? 'Thinking...' : 'Run Analysis'}</Button>
          </div>
        </CardContent>
      </Card>

      <Card className="col-span-1 md:col-span-1">
        <CardHeader>
          <CardTitle>AI Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="italic text-sm text-muted-foreground">Thinking... this may take a few seconds.</div>
          ) : error ? (
            <div className="text-sm text-red-600">{error}</div>
          ) : analysis ? (
            MarkdownComponent ? (
              <MarkdownComponent>{analysis}</MarkdownComponent>
            ) : (
              <pre className="whitespace-pre-wrap text-sm">{analysis}</pre>
            )
          ) : (
            <div className="text-sm text-muted-foreground">No analysis yet. Run the analysis to see results.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
