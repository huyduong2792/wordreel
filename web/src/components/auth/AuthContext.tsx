import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { api, type User, type AuthToken } from '../../lib/api';
import { supabase, signOut as supabaseSignOut } from '../../lib/supabase';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, username: string, password: string) => Promise<void>;
    logout: () => void;
    showAuthModal: boolean;
    setShowAuthModal: (show: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [showAuthModal, setShowAuthModal] = useState(false);

    // Check for existing session on mount and listen for auth changes
    useEffect(() => {
        // First, check localStorage for existing user (faster initial load)
        const savedUser = localStorage.getItem('wordreel_user');
        if (savedUser) {
            try {
                setUser(JSON.parse(savedUser));
            } catch {
                localStorage.removeItem('wordreel_token');
                localStorage.removeItem('wordreel_user');
            }
        }

        // Then, check Supabase session (handles OAuth tokens)
        const initSession = async () => {
            try {
                const { data: { session } } = await supabase.auth.getSession();
                if (session?.user) {
                    const supabaseUser = session.user;
                    const userData: User = {
                        id: supabaseUser.id,
                        email: supabaseUser.email || '',
                        username: supabaseUser.user_metadata?.full_name || 
                                  supabaseUser.email?.split('@')[0] || 'User',
                        avatar_url: supabaseUser.user_metadata?.avatar_url,
                        created_at: supabaseUser.created_at,
                    };
                    setUser(userData);
                    localStorage.setItem('wordreel_user', JSON.stringify(userData));
                    localStorage.setItem('wordreel_token', session.access_token);
                }
            } catch (error) {
                console.error('Failed to get Supabase session:', error);
            } finally {
                setIsLoading(false);
            }
        };

        initSession();

        // Listen for auth state changes (login, logout, token refresh)
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (event, session) => {
                console.log('Auth state changed:', event);
                
                if (event === 'SIGNED_IN' && session?.user) {
                    const supabaseUser = session.user;
                    const userData: User = {
                        id: supabaseUser.id,
                        email: supabaseUser.email || '',
                        username: supabaseUser.user_metadata?.full_name || 
                                  supabaseUser.email?.split('@')[0] || 'User',
                        avatar_url: supabaseUser.user_metadata?.avatar_url,
                        created_at: supabaseUser.created_at,
                    };
                    setUser(userData);
                    localStorage.setItem('wordreel_user', JSON.stringify(userData));
                    localStorage.setItem('wordreel_token', session.access_token);
                    setShowAuthModal(false);
                } else if (event === 'SIGNED_OUT') {
                    setUser(null);
                    localStorage.removeItem('wordreel_user');
                    localStorage.removeItem('wordreel_token');
                } else if (event === 'TOKEN_REFRESHED' && session) {
                    localStorage.setItem('wordreel_token', session.access_token);
                }
            }
        );

        return () => {
            subscription.unsubscribe();
        };
    }, []);

    const login = async (email: string, password: string) => {
        const result = await api.login(email, password);
        setUser(result.user);
        localStorage.setItem('wordreel_user', JSON.stringify(result.user));
        setShowAuthModal(false);
    };

    const register = async (email: string, username: string, password: string) => {
        const result = await api.register(email, username, password);
        setUser(result.user);
        localStorage.setItem('wordreel_user', JSON.stringify(result.user));
        setShowAuthModal(false);
    };

    const logout = async () => {
        try {
            // Sign out from Supabase (handles OAuth sessions)
            await supabaseSignOut();
        } catch (error) {
            console.error('Supabase sign out error:', error);
        }
        
        // Also clear local auth state
        api.logout();
        setUser(null);
        localStorage.removeItem('wordreel_user');
        localStorage.removeItem('wordreel_token');
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                isLoading,
                login,
                register,
                logout,
                showAuthModal,
                setShowAuthModal,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
