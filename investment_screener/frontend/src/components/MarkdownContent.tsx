import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

interface Props {
    content: string;
    accentColor?: 'indigo' | 'amber' | 'emerald';
}

export default function MarkdownContent({ content, accentColor = 'indigo' }: Props) {
    const cleaned = content.replace(/<!--[\s\S]*?-->/g, '').replace(/\n{3,}/g, '\n\n').trim();

    const accent = {
        indigo: { text: 'text-indigo-400', border: 'border-indigo-500/40', bg: 'bg-indigo-500/10', code: 'text-indigo-300', link: 'text-indigo-400 hover:text-indigo-300' },
        amber:  { text: 'text-amber-400',  border: 'border-amber-500/40',  bg: 'bg-amber-500/10',  code: 'text-amber-300',  link: 'text-amber-400 hover:text-amber-300' },
        emerald:{ text: 'text-emerald-400',border: 'border-emerald-500/40',bg: 'bg-emerald-500/10',code: 'text-emerald-300',link: 'text-emerald-400 hover:text-emerald-300' },
    }[accentColor];

    const components: Components = {
        h1: ({ children }) => (
            <h1 className="text-xl font-bold text-white tracking-tight mt-8 mb-4 pb-3 border-b border-slate-700 first:mt-0">
                {children}
            </h1>
        ),
        h2: ({ children }) => (
            <h2 className={`text-base font-bold text-white tracking-tight mt-8 mb-3 flex items-center gap-2`}>
                <span className={`w-1 h-4 rounded-full ${accent.text} bg-current opacity-80 shrink-0`} />
                {children}
            </h2>
        ),
        h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-widest mt-6 mb-2">
                {children}
            </h3>
        ),
        h4: ({ children }) => (
            <h4 className="text-sm font-semibold text-slate-300 mt-4 mb-1">{children}</h4>
        ),
        p: ({ children }) => (
            <p className="text-slate-300 text-sm leading-relaxed my-2">{children}</p>
        ),
        strong: ({ children }) => (
            <strong className="text-white font-semibold">{children}</strong>
        ),
        em: ({ children }) => (
            <em className="text-slate-400 not-italic">{children}</em>
        ),
        blockquote: ({ children }) => (
            <blockquote className={`border-l-2 ${accent.border} ${accent.bg} pl-4 pr-3 py-2 my-4 rounded-r-lg text-slate-400 text-sm`}>
                {children}
            </blockquote>
        ),
        ul: ({ children }) => <ul className="my-3 space-y-1 list-disc list-inside">{children}</ul>,
        ol: ({ children }) => <ol className="my-3 space-y-1 list-decimal list-inside">{children}</ol>,
        li: ({ children }) => <li className="text-slate-300 text-sm leading-relaxed">{children}</li>,
        hr: () => <hr className="border-slate-700/60 my-6" />,
        a: ({ href, children }) => (
            <a href={href} className={`${accent.link} underline-offset-2 hover:underline transition-colors`} target="_blank" rel="noopener noreferrer">
                {children}
            </a>
        ),
        code: ({ className, children, ...props }) => {
            const isBlock = !!className;
            return isBlock ? (
                <code className={`${className} text-slate-200 text-xs font-mono`} {...props}>{children}</code>
            ) : (
                <code className={`${accent.code} bg-slate-800/80 px-1.5 py-0.5 rounded text-xs font-mono`} {...props}>{children}</code>
            );
        },
        pre: ({ children }) => (
            <pre className="bg-slate-900 border border-slate-700/60 rounded-xl text-xs my-4 p-4 overflow-x-auto font-mono">
                {children}
            </pre>
        ),
        table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
                <table className="w-full text-sm border border-slate-700/60 rounded-lg overflow-hidden border-separate border-spacing-0">
                    {children}
                </table>
            </div>
        ),
        thead: ({ children }) => (
            <thead className="bg-slate-800/60 border-b border-slate-700">{children}</thead>
        ),
        th: ({ children }) => (
            <th className="text-left text-[10px] font-black uppercase tracking-widest text-slate-400 px-3 py-2.5">
                {children}
            </th>
        ),
        td: ({ children }) => (
            <td className="text-slate-300 text-xs px-3 py-2 border-b border-slate-800/60">
                {children}
            </td>
        ),
        tr: ({ children }) => (
            <tr className="hover:bg-white/[0.02] transition-colors">{children}</tr>
        ),
    };

    return (
        <div className="max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
                {cleaned}
            </ReactMarkdown>
        </div>
    );
}

