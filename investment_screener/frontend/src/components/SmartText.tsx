/**
 * SmartText.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Enhances text by automatically linking financial terms to their help definitions.
 *
 * Layer: Frontend / UI / Components
 *
 * Usage Examples:
 *     <SmartText text="The P/S ratio is high." />
 *
 * Key Functions:
 *     - openHelp() - Hook-driven function to trigger the Help Modal for a specific topic ID
 *     - SmartText() - Functional component that tokenizes text using regex and injects interactive help triggers
 *     - withFinancialHelp() - Preserve formatted prose and source links while linking financial terms
 */
import React from 'react';
import { useHelpModal } from './HelpModal';
import { HelpCircle } from 'lucide-react';

// Dictionary of terms to link and their Help Modal ID
const SMART_LINKS: { [key: string]: string } = {
    "Discounted Cash Flow": "dcf",
    "DCF": "dcf",
    "Weighted Average Cost of Capital": "wacc",
    "WACC": "wacc",
    "Cost of Equity": "costOfEquity",
    "Rule of 40": "ruleOf40",
    "Piotroski": "piotroskiScore",
    "F-Score": "piotroskiScore",
    "Forward P/E": "forwardPE",
    "Exit P/E": "exitPE",
    "PEG Ratio": "pegRatio",
    "Beta": "beta",
    "Discount Rate": "discountRate",
    "Free Cash Flow": "freeCashFlow",
    "Operating Margin": "operatingMargin",
    "Net Margin": "netMargin",
    "Gross Margin": "grossMargin",
    "Revenue Growth": "revenueGrowth",
    "CAGR": "cagr",
    "Moat": "moatAnalysis",
    "Operating Leverage": "operatingLeverage",
    "Share Buybacks": "shareChange",
    "Dilution": "shareChange",
    "21 EMA": "emaAlignment",
    "50 EMA": "emaAlignment",
    "200 EMA": "emaAlignment",
    "EMA Stack": "emaAlignment",
    "Multi-EMA": "emaAlignment",
    "ADX": "adx",
    "Volume Bias": "volBias",
    "ATR": "atr",
    "Squeeze": "ttmSqueeze",
    "TTM Squeeze": "ttmSqueeze"
};

/** Link prose text without creating help buttons inside source links or code. */
export function withFinancialHelp(children: React.ReactNode): React.ReactNode {
    return React.Children.map(children, child => {
        if (typeof child === 'string') return <SmartText text={child} />;
        if (!React.isValidElement<{ children?: React.ReactNode }>(child)) return child;
        if (['a', 'button', 'code', 'pre'].includes(String(child.type))) return child;
        return React.cloneElement(child, undefined, withFinancialHelp(child.props.children));
    });
}

interface SmartTextProps {
    text: string;
    className?: string;
}

export const SmartText: React.FC<SmartTextProps> = ({ text, className = "" }) => {
    const { openHelp } = useHelpModal();

    if (!text) return null;

    // Create a regex to match any key in SMART_LINKS via explicit keywords
    // We sort by length descending to match "Operating Margin" before "Margin" if both existed
    const terms = Object.keys(SMART_LINKS).sort((a, b) => b.length - a.length);
    const escapedTerms = terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const regex = new RegExp(`\\b(${escapedTerms.join('|')})\\b`, 'gi');

    const parts = text.split(regex);

    return (
        <span className={className}>
            {parts.map((part, i) => {
                // Check if this part matches a known term (case-insensitive find)
                const matchedKey = terms.find(t => t.toLowerCase() === part.toLowerCase());

                if (matchedKey) {
                    const topicId = SMART_LINKS[matchedKey];
                    return (
                        <button
                            key={i}
                            type="button"
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                openHelp(topicId);
                            }}
                            className="inline-flex items-baseline gap-0.5 group cursor-help transition-colors text-indigo-300 hover:text-indigo-200 decoration-dotted decoration-indigo-500/50 underline underline-offset-2"
                        >
                            {part}
                            <HelpCircle size={10} className="opacity-70 group-hover:opacity-100" />
                        </button>
                    );
                }
                return <span key={i}>{part}</span>;
            })}
        </span>
    );
};
