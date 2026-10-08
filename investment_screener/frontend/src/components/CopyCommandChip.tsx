/**
 * Purpose: a reminder chip that copies an agent slash command, for actions the web app cannot run itself.
 * Layer: Frontend / UI. Usage: <CopyCommandChip command="/questrade-sync-portfolio" label="Refresh trades via" />.
 * Key Functions: CopyCommandChip — copy-on-click with a brief confirmation.
 * Key Input Dependencies: browser clipboard API.
 */
import { useState } from 'react';
import { Check, Sparkles } from 'lucide-react';

export function CopyCommandChip({ command, label, title, highlight = false }: {
    command: string; label: string; title?: string; highlight?: boolean;
}) {
    const [copied, setCopied] = useState(false);
    const copy = async () => {
        try { await navigator.clipboard.writeText(command); } catch { /* clipboard blocked: the command is still visible */ }
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2000);
    };
    return (
        <button type="button" onClick={copy} title={title}
            className={`text-[11px] font-semibold px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 transition-all shadow-sm border ${
                highlight ? 'text-amber-200 bg-amber-950/60 hover:bg-amber-900/70 border-amber-500/50'
                    : 'text-indigo-300 bg-indigo-950/60 hover:bg-indigo-900/80 border-indigo-500/40'}`}>
            {copied ? <Check size={13} className="text-emerald-400" /> : <Sparkles size={13} className={highlight ? 'text-amber-400' : 'text-indigo-400'} />}
            {copied ? `Copied ${command}!` : `${label} ${command}`}
        </button>
    );
}
