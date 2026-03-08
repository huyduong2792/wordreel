import React, { useState, useRef, useEffect } from 'react';
import { User, LogOut, Settings, BookOpen, Trophy, ChevronDown } from 'lucide-react';
import { useAuth } from './AuthContext';

export const UserMenu: React.FC = () => {
    const { user, logout, setShowAuthModal } = useAuth();
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    if (!user) {
        return (
            <button
                onClick={() => setShowAuthModal(true)}
                className="px-4 py-2 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-bold rounded-md transition-colors text-sm"
            >
                Log in
            </button>
        );
    }

    return (
        <div ref={menuRef} className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 p-1 pr-3 bg-white/10 hover:bg-white/20 rounded-full transition-colors"
            >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#fe2c55] to-[#ff6b35] flex items-center justify-center text-white font-bold text-sm">
                    {user.username?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                </div>
                <ChevronDown 
                    size={16} 
                    className={`text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
                />
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-[#1a1a1a] border border-gray-800 rounded-xl overflow-hidden shadow-xl animate-in fade-in slide-in-from-top-2 duration-200 z-50">
                    {/* User Info */}
                    <div className="p-4 border-b border-gray-800">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#fe2c55] to-[#ff6b35] flex items-center justify-center text-white font-bold text-lg">
                                {user.username?.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-bold text-white truncate">
                                    {user.username || 'User'}
                                </p>
                                <p className="text-sm text-gray-400 truncate">
                                    {user.email}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                        <button className="w-full px-4 py-3 flex items-center gap-3 text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
                            <User size={20} />
                            <span>View profile</span>
                        </button>
                        <button className="w-full px-4 py-3 flex items-center gap-3 text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
                            <BookOpen size={20} />
                            <span>My learning</span>
                        </button>
                        <button className="w-full px-4 py-3 flex items-center gap-3 text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
                            <Trophy size={20} />
                            <span>Achievements</span>
                        </button>
                        <button className="w-full px-4 py-3 flex items-center gap-3 text-gray-300 hover:bg-white/5 hover:text-white transition-colors">
                            <Settings size={20} />
                            <span>Settings</span>
                        </button>
                    </div>

                    {/* Logout */}
                    <div className="border-t border-gray-800 py-2">
                        <button 
                            onClick={() => {
                                logout();
                                setIsOpen(false);
                            }}
                            className="w-full px-4 py-3 flex items-center gap-3 text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
                        >
                            <LogOut size={20} />
                            <span>Log out</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
