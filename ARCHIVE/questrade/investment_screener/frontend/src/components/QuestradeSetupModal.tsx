/**
 * QuestradeSetupModal.tsx (React Component)
 * =====================================
 *
 * Purpose:
 *     Interactive setup guide for Questrade API token seeding and account synchronization.
 *
 * Layer: Frontend / UI / Modals
 *
 * Usage Examples:
 *     <QuestradeSetupModal isOpen={true} onClose={() => {}} />
 *
 * Key Functions:
 *     - seedQuestradeToken() - Initiates the OAuth exchange and token persistence
 *     - syncQuestrade() - Triggers a background sync of accounts and positions
 */
import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { seedQuestradeToken, syncQuestrade } from '../services/api';

interface QuestradeSetupModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSyncComplete: () => void;
}

type Step = 'INTRO' | 'INPUT' | 'SUCCESS';

export const QuestradeSetupModal: React.FC<QuestradeSetupModalProps> = ({ isOpen, onClose, onSyncComplete }) => {
    const [step, setStep] = useState<Step>('INTRO');
    const [token, setToken] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSeed = async () => {
        if (!token.trim()) return;
        setLoading(true);
        setError(null);
        try {
            await seedQuestradeToken(token.trim());
            setStep('SUCCESS');
        } catch (err: any) {
            setError(err.message || 'Failed to seed token');
        } finally {
            setLoading(false);
        }
    };

    const handleInitialSync = async () => {
        setLoading(true);
        setError(null);
        try {
            await syncQuestrade();
            onSyncComplete();
            onClose();
        } catch (err: any) {
            setError(err.message || 'Initial sync failed');
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[9999] p-4">
            <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-lg shadow-[0_0_50px_-12px_rgba(245,158,11,0.3)] animate-in fade-in zoom-in duration-300">

                {/* Header */}
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h2 className="text-2xl font-bold text-white tracking-tight">Questrade Integration</h2>
                        <p className="text-gray-400 text-sm mt-1">Securely link your brokerage account</p>
                    </div>
                    <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Content */}
                <div className="space-y-6">
                    {step === 'INTRO' && (
                        <div className="space-y-4 animate-in slide-in-from-right-4 duration-300">
                            <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-amber-200 text-sm">
                                <strong>Manual Setup Required:</strong> Questrade requires a one-time manual "Refresh Token" to initialize the secure bridge.
                            </div>
                            <ol className="space-y-3 text-gray-300 text-sm list-decimal list-inside">
                                <li>Log in to <a href="https://apphub.questrade.com/UI/UserApps.aspx" target="_blank" rel="noopener" className="text-amber-400 hover:underline">Questrade App Hub</a></li>
                                <li>Click <strong>API Centre</strong> on your application</li>
                                <li>Click <strong>Generate Token</strong> to get a One-Week Token</li>
                                <li>Copy and paste it below — we'll exchange it automatically</li>
                            </ol>
                            <button
                                onClick={() => setStep('INPUT')}
                                className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold py-3 rounded-xl transition-all shadow-lg shadow-amber-500/20"
                            >
                                I have my token
                            </button>
                        </div>
                    )}

                    {step === 'INPUT' && (
                        <div className="space-y-4 animate-in slide-in-from-right-4 duration-300">
                            <div>
                                <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">One-Week Token</label>
                                <input
                                    type="text"
                                    value={token}
                                    onChange={(e) => setToken(e.target.value)}
                                    placeholder="Paste your one-week token here..."
                                    className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none transition-all font-mono text-sm"
                                />
                                {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setStep('INTRO')}
                                    className="flex-1 bg-gray-800 hover:bg-gray-700 text-white font-semibold py-3 rounded-xl transition-all"
                                >
                                    Back
                                </button>
                                <button
                                    onClick={handleSeed}
                                    disabled={loading || !token}
                                    className="flex-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 disabled:hover:bg-amber-500 text-black font-bold py-3 px-8 rounded-xl transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center"
                                >
                                    {loading ? (
                                        <svg className="animate-spin h-5 w-5 text-black" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                    ) : 'Verify & Link'}
                                </button>
                            </div>
                        </div>
                    )}

                    {step === 'SUCCESS' && (
                        <div className="text-center space-y-6 animate-in zoom-in-95 duration-300">
                            <div className="w-20 h-20 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4 border border-green-500/30">
                                <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                </svg>
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-white">Securely Linked!</h3>
                                <p className="text-gray-400 text-sm mt-2">Your token is encrypted and stored in the hardware-backed Keychain. Your master key never leaves your system.</p>
                            </div>
                            <button
                                onClick={handleInitialSync}
                                disabled={loading}
                                className="w-full bg-white hover:bg-gray-100 text-black font-bold py-3 rounded-xl transition-all shadow-xl flex items-center justify-center"
                            >
                                {loading ? 'Fetching Portfolio...' : 'Sync Positions Now'}
                            </button>
                        </div>
                    )}
                </div>

                {/* Security Badge */}
                <div className="mt-8 pt-6 border-t border-gray-800 flex items-center justify-center gap-2 text-gray-500 text-[10px] font-semibold uppercase tracking-widest">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    AES-GCM Encrypted Bridge
                </div>
            </div>
        </div>,
        document.body
    );
};
