import React, { useState, useEffect } from 'react';
import { AuthProvider, AuthModal, UserMenu, useAuth } from '../auth';
import { VideoFeed } from '../video/VideoFeed';
import { CommentsPanel } from '../video/CommentsPanel';
import { Home, Compass, Search, ChevronUp, ChevronDown, Upload, Radio, User } from 'lucide-react';
import { api } from '../../lib/api';

interface AppContentProps {
    initialPostId?: string;
    sessionReady: boolean;
}

// Inner component that uses auth context
const AppContent: React.FC<AppContentProps> = ({ initialPostId, sessionReady }) => {
    const { showAuthModal, setShowAuthModal, isAuthenticated } = useAuth();
    const [activePostId, setActivePostId] = useState<string>('');
    const [activeCommentsCount, setActiveCommentsCount] = useState<number>(0);

    return (
        <div className="flex h-screen bg-black overflow-hidden">
            {/* Sidebar - Desktop Only (TikTok style) */}
            <aside className="hidden lg:flex flex-col w-[240px] flex-shrink-0 px-3 py-5">
                {/* Logo */}
                <a 
                    href="/"
                    className="flex items-center gap-2 mb-5 px-3 cursor-pointer hover:opacity-80 transition-opacity"
                >
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#fe2c55] to-[#25f4ee] flex items-center justify-center">
                        <span className="text-white font-bold text-xl">W</span>
                    </div>
                    <span className="text-xl font-bold text-white">WordReel</span>
                </a>

                {/* Search Input */}
                <div className="px-3 mb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                        <input 
                            type="text"
                            placeholder="Search"
                            className="w-full bg-[#2f2f2f] text-white placeholder-gray-400 rounded-full py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-gray-600"
                        />
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 space-y-1">
                    <SidebarItem icon={<Home size={24} />} label="For You" active href="/" />
                    <SidebarItem icon={<Compass size={24} />} label="Explore" href="/explore" />
                </nav>

                {/* Login Button */}
                <div className="px-3 mb-6">
                    {!isAuthenticated && (
                        <button
                            onClick={() => setShowAuthModal(true)}
                            className="w-full py-3 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-semibold rounded-md transition-colors"
                        >
                            Log in
                        </button>
                    )}
                </div>

                {/* Footer Links */}
                <div className="px-3 text-xs text-gray-500 space-y-2">
                    <div className="space-x-2">
                        <a href="#" className="hover:underline">Company</a>
                        <a href="#" className="hover:underline">Program</a>
                    </div>
                    <div className="space-x-2">
                        <a href="#" className="hover:underline">Terms & Policies</a>
                    </div>
                    <p className="text-gray-600">© 2025 WordReel</p>
                </div>
            </aside>

            {/* Main Content Area - Video Feed */}
            <main className="flex-1 flex justify-center overflow-hidden">
                <div className="w-full h-full">
                    <VideoFeed 
                        onActivePostChange={(postId, commentsCount) => {
                            setActivePostId(postId);
                            setActiveCommentsCount(commentsCount);
                        }}
                        initialPostId={initialPostId}
                        sessionReady={sessionReady}
                    />
                </div>
            </main>

            {/* Right Panel - Desktop Only */}
            <div className="hidden lg:flex flex-col w-[400px] flex-shrink-0">
                {/* Top Right Actions */}
                <div className="flex items-center justify-end gap-2 p-4">
                    {isAuthenticated ? (
                        <UserMenu />
                    ) : (
                        <button
                            onClick={() => setShowAuthModal(true)}
                            className="px-4 py-1.5 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-semibold rounded-md transition-colors text-sm"
                        >
                            Log in
                        </button>
                    )}
                </div>

                {/* Comments Panel */}
                <div className="flex-1 overflow-hidden">
                    {activePostId ? (
                        <CommentsPanel 
                            postId={activePostId} 
                            commentsCount={activeCommentsCount}
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-500">
                            <p>Select a video to see comments</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation Arrows - Fixed position to the left of right panel */}
            <div className="hidden lg:flex fixed right-[420px] top-1/2 -translate-y-1/2 flex-col gap-3 z-50">
                <button className="w-12 h-12 bg-[#2f2f2f] hover:bg-[#3f3f3f] rounded-full flex items-center justify-center transition-colors">
                    <ChevronUp className="text-white" size={24} />
                </button>
                <button className="w-12 h-12 bg-[#2f2f2f] hover:bg-[#3f3f3f] rounded-full flex items-center justify-center transition-colors">
                    <ChevronDown className="text-white" size={24} />
                </button>
            </div>

            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-black/90 backdrop-blur-sm">
                <div className="flex items-center justify-between px-4 py-3">
                    <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#fe2c55] to-[#25f4ee] flex items-center justify-center">
                            <span className="text-white font-bold">W</span>
                        </div>
                        <span className="font-bold text-white">WordReel</span>
                    </a>

                    {isAuthenticated ? (
                        <UserMenu />
                    ) : (
                        <button
                            onClick={() => setShowAuthModal(true)}
                            className="px-4 py-2 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-bold rounded-md transition-colors text-sm"
                        >
                            Log in
                        </button>
                    )}
                </div>
            </header>

            {/* Bottom Navigation - Mobile Only */}
            <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-black border-t border-gray-800/50 px-2 py-2 flex items-center justify-around">
                <BottomNavItem icon={<Home size={24} />} label="Home" active href="/" />
                <BottomNavItem icon={<Compass size={24} />} label="Discover" href="/explore" />
                <button className="p-2 bg-white rounded-lg">
                    <Upload size={24} className="text-black" />
                </button>
                <BottomNavItem icon={<Radio size={24} />} label="Inbox" />
                <BottomNavItem 
                    icon={
                        isAuthenticated ? (
                            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[#fe2c55] to-[#25f4ee] flex items-center justify-center text-white font-bold text-xs">
                                U
                            </div>
                        ) : (
                            <User size={24} />
                        )
                    } 
                    label="Profile"
                    onClick={() => !isAuthenticated && setShowAuthModal(true)}
                />
            </nav>

            {/* Auth Modal */}
            <AuthModal 
                isOpen={showAuthModal} 
                onClose={() => setShowAuthModal(false)} 
            />
        </div>
    );
};

// Sidebar Item Component
export const SidebarItem: React.FC<{
    icon: React.ReactNode;
    label: string;
    active?: boolean;
    href?: string;
}> = ({ icon, label, active, href }) =>
    href ? (
        <a href={href} className={`w-full px-4 py-3 flex items-center gap-4 rounded-lg transition-colors ${active ? 'text-white font-bold' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
            {icon}
            <span>{label}</span>
        </a>
    ) : (
        <button
            className={`w-full px-4 py-3 flex items-center gap-4 rounded-lg transition-colors ${active ? 'text-white font-bold' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
        >
            {icon}
            <span>{label}</span>
        </button>
    );

// Bottom Nav Item Component  
const BottomNavItem: React.FC<{
    icon: React.ReactNode;
    label: string;
    active?: boolean;
    href?: string;
    onClick?: () => void;
}> = ({ icon, label, active, href, onClick }) =>
    href ? (
        <a
            href={href}
            className={`flex flex-col items-center gap-1 px-3 py-1 ${
                active ? 'text-white' : 'text-gray-500'
            }`}
        >
            {icon}
            <span className="text-[10px]">{label}</span>
        </a>
    ) : (
        <button
            onClick={onClick}
            className={`flex flex-col items-center gap-1 px-3 py-1 ${
                active ? 'text-white' : 'text-gray-500'
            }`}
        >
            {icon}
            <span className="text-[10px]">{label}</span>
        </button>
    );

interface AppProps {
    initialPostId?: string;
}

// Main App with Provider
export const App: React.FC<AppProps> = ({ initialPostId }) => {
    const [sessionReady, setSessionReady] = useState(false);
    
    // Initialize session once at app level
    useEffect(() => {
        api.initSession()
            .then(() => setSessionReady(true))
            .catch(() => setSessionReady(true)); // Continue anyway
    }, []);
    
    return (
        <AuthProvider>
            <AppContent initialPostId={initialPostId} sessionReady={sessionReady} />
        </AuthProvider>
    );
};
