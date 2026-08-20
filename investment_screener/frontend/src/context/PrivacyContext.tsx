/**
 * PrivacyContext.tsx (React Global Context)
 * ========================================
 *
 * Purpose:
 *     Provides a global Privacy / Demo Mode state across the frontend application.
 *     When enabled:
 *       - Monetary amounts ($ total values, market value, P&L $, account balances)
 *         are masked with clean visual blocks (e.g. "$••,•••" or blurred).
 *       - Persisted in localStorage so screenshots remain privacy-safe across refreshes.
 *
 * Layer: Frontend / Context
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

interface PrivacyContextType {
    isPrivacyMode: boolean;
    togglePrivacyMode: () => void;
    formatPrivateMoney: (amount: number | string | null | undefined, formatter?: (v: number) => string) => string;
}

const PrivacyContext = createContext<PrivacyContextType>({
    isPrivacyMode: false,
    togglePrivacyMode: () => {},
    formatPrivateMoney: () => '',
});

const STORAGE_KEY = 'investment_toolkit_privacy_mode';

export const PrivacyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isPrivacyMode, setIsPrivacyMode] = useState<boolean>(() => {
        try {
            return localStorage.getItem(STORAGE_KEY) === 'true';
        } catch {
            return false;
        }
    });

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, String(isPrivacyMode));
        } catch {
            // ignore localStorage quota errors
        }
    }, [isPrivacyMode]);

    const togglePrivacyMode = () => {
        setIsPrivacyMode(prev => !prev);
    };

    const formatPrivateMoney = (
        amount: number | string | null | undefined,
        formatter?: (v: number) => string
    ): string => {
        if (amount == null) return '—';
        if (isPrivacyMode) {
            return '$••••••';
        }
        if (typeof amount === 'string') return amount;
        if (formatter) return formatter(amount);
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
    };

    return (
        <PrivacyContext.Provider value={{ isPrivacyMode, togglePrivacyMode, formatPrivateMoney }}>
            {children}
        </PrivacyContext.Provider>
    );
};

export const usePrivacy = () => useContext(PrivacyContext);
