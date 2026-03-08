import React, { useState } from 'react';
import { X, Mail, Lock, User, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from './AuthContext';
import { GoogleLoginButton } from './GoogleLoginButton';

type AuthMode = 'login' | 'register';

interface AuthModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
    const { login, register } = useAuth();
    const [mode, setMode] = useState<AuthMode>('login');
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            if (mode === 'login') {
                await login(email, password);
            } else {
                if (!username.trim()) {
                    throw new Error('Username is required');
                }
                await register(email, username, password);
            }
            // Reset form
            setEmail('');
            setUsername('');
            setPassword('');
        } catch (err: any) {
            setError(err.message || 'Authentication failed');
        } finally {
            setIsLoading(false);
        }
    };

    const switchMode = () => {
        setMode(mode === 'login' ? 'register' : 'login');
        setError(null);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div 
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
                onClick={onClose}
            />
            
            {/* Modal */}
            <div className="relative w-full max-w-md mx-4 bg-[#121212] rounded-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="relative p-6 pb-4">
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X size={20} />
                    </button>
                    
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-white mb-2">
                            {mode === 'login' ? 'Log in to WordReel' : 'Sign up for WordReel'}
                        </h2>
                        <p className="text-gray-400 text-sm">
                            {mode === 'login' 
                                ? 'Manage your account, check notifications, comment on videos, and more.'
                                : 'Create an account to save progress, take quizzes, and track your learning.'
                            }
                        </p>
                    </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="px-6 pb-6">
                    {/* Error message */}
                    {error && (
                        <div className="flex items-center gap-2 p-3 mb-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    <div className="space-y-4">
                        {/* Email Input */}
                        <div className="relative">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                                <Mail size={20} />
                            </div>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="Email"
                                required
                                className="w-full pl-12 pr-4 py-4 bg-[#2a2a2a] border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#fe2c55] focus:ring-1 focus:ring-[#fe2c55] transition-colors"
                            />
                        </div>

                        {/* Username Input (Register only) */}
                        {mode === 'register' && (
                            <div className="relative">
                                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                                    <User size={20} />
                                </div>
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    placeholder="Username"
                                    required
                                    className="w-full pl-12 pr-4 py-4 bg-[#2a2a2a] border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#fe2c55] focus:ring-1 focus:ring-[#fe2c55] transition-colors"
                                />
                            </div>
                        )}

                        {/* Password Input */}
                        <div className="relative">
                            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">
                                <Lock size={20} />
                            </div>
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Password"
                                required
                                minLength={6}
                                className="w-full pl-12 pr-12 py-4 bg-[#2a2a2a] border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-[#fe2c55] focus:ring-1 focus:ring-[#fe2c55] transition-colors"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                            >
                                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                            </button>
                        </div>

                        {/* Forgot Password (Login only) */}
                        {mode === 'login' && (
                            <div className="text-right">
                                <button
                                    type="button"
                                    className="text-sm text-gray-400 hover:text-white transition-colors"
                                >
                                    Forgot password?
                                </button>
                            </div>
                        )}

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full py-4 bg-[#fe2c55] hover:bg-[#ef2950] disabled:bg-[#fe2c55]/50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 size={20} className="animate-spin" />
                                    {mode === 'login' ? 'Logging in...' : 'Creating account...'}
                                </>
                            ) : (
                                mode === 'login' ? 'Log in' : 'Sign up'
                            )}
                        </button>
                    </div>

                    {/* Divider */}
                    <div className="flex items-center gap-4 my-6">
                        <div className="flex-1 h-px bg-gray-700" />
                        <span className="text-gray-500 text-sm">OR</span>
                        <div className="flex-1 h-px bg-gray-700" />
                    </div>

                    {/* Social Login */}
                    <div className="space-y-3">
                        <GoogleLoginButton 
                            onError={(error) => setError(error.message)}
                        />
                    </div>
                </form>

                {/* Footer */}
                <div className="px-6 py-4 bg-[#1a1a1a] border-t border-gray-800 text-center">
                    <p className="text-gray-400 text-sm">
                        {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
                        <button
                            type="button"
                            onClick={switchMode}
                            className="text-[#fe2c55] font-semibold hover:underline"
                        >
                            {mode === 'login' ? 'Sign up' : 'Log in'}
                        </button>
                    </p>
                </div>

                {/* Terms (Register only) */}
                {mode === 'register' && (
                    <div className="px-6 pb-4 text-center">
                        <p className="text-xs text-gray-500">
                            By continuing, you agree to WordReel's{' '}
                            <a href="#" className="text-gray-400 hover:underline">Terms of Service</a>
                            {' '}and confirm that you have read WordReel's{' '}
                            <a href="#" className="text-gray-400 hover:underline">Privacy Policy</a>.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};
