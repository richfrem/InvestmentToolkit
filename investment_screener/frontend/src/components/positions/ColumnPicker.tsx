/**
 * ColumnPicker.tsx - The "Columns" menu: show or hide each column and reorder them.
 *
 * Purpose:
 *     One picker for every configurable table. It lists the registry's columns in the current
 *     order with a checkbox and up/down buttons, and a reset to the preset's defaults.
 *
 * Layer: Frontend / Components / Positions
 *
 * Usage Examples:
 *     <ColumnPicker order={order} visible={visible} columns={COLUMNS} onToggle={toggle} onMove={move} onReset={reset} />
 *
 * Key Functions (Index):
 *     - ColumnPicker: button plus dropdown list
 *
 * Key Input Dependencies:
 *     - PositionColumn (label, always)
 *
 * Key Output Dependencies:
 *     - PortfolioPage toolbar
 */
import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, SlidersHorizontal } from 'lucide-react';
import type { PositionColumn } from './columns';

interface ColumnPickerProps {
    order: string[];
    visible: Set<string>;
    columns: PositionColumn[];
    onToggle: (id: string) => void;
    onMove: (id: string, direction: 'up' | 'down') => void;
    onReset: () => void;
}

export function ColumnPicker({ order, visible, columns, onToggle, onMove, onReset }: ColumnPickerProps) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    const byId = new Map(columns.map(c => [c.id, c]));

    useEffect(() => {
        const close = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
        document.addEventListener('mousedown', close);
        return () => document.removeEventListener('mousedown', close);
    }, []);

    return (
        <div className="relative" ref={ref}>
            <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
                className="flex items-center gap-1.5 rounded bg-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-700">
                <SlidersHorizontal size={13} /> Columns
            </button>
            {open && (
                <div role="menu" aria-label="Configure columns"
                    className="absolute right-0 top-8 z-50 max-h-96 w-64 overflow-y-auto rounded-lg border border-zinc-700 bg-zinc-800 p-2 shadow-2xl">
                    <div className="mb-1 flex items-center justify-between border-b border-zinc-700 px-2 pb-1">
                        <span className="text-[10px] font-bold uppercase text-zinc-500">Configure columns</span>
                        <button type="button" onClick={onReset} className="text-[10px] font-bold text-amber-400 hover:text-amber-300">Reset</button>
                    </div>
                    {order.map((id, index) => {
                        const col = byId.get(id);
                        if (!col) return null;
                        return (
                            <div key={id} className="group flex items-center justify-between rounded px-2 py-1.5 hover:bg-zinc-700">
                                <label className="flex flex-1 cursor-pointer items-center gap-2">
                                    <input type="checkbox" disabled={col.always} checked={visible.has(id)} onChange={() => onToggle(id)}
                                        className="h-3.5 w-3.5 accent-amber-500" />
                                    <span className={`text-xs ${visible.has(id) ? 'text-zinc-200' : 'text-zinc-500'}`}>{col.label}</span>
                                </label>
                                <span className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                                    <button type="button" aria-label={`Move ${col.label} up`} disabled={index === 0} onClick={() => onMove(id, 'up')}
                                        className="rounded p-1 text-zinc-400 hover:bg-zinc-600 disabled:text-zinc-700"><ArrowUp size={12} /></button>
                                    <button type="button" aria-label={`Move ${col.label} down`} disabled={index === order.length - 1} onClick={() => onMove(id, 'down')}
                                        className="rounded p-1 text-zinc-400 hover:bg-zinc-600 disabled:text-zinc-700"><ArrowDown size={12} /></button>
                                </span>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
