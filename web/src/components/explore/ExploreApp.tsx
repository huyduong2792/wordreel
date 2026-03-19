import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from '../auth';
import { CategoryTabs } from './CategoryTabs';
import { ExploreGrid } from './ExploreGrid';
import { Home, Compass, Search, Upload, Radio, User } from 'lucide-react';
import { SidebarItem } from '../app/App';

interface ExploreAppProps {}

const ExploreContent: React.FC = () => {
    const { showAuthModal, setShowAuthModal, isAuthenticated } = useAuth();
    const [activeTag, setActiveTag] = useState<string | null>(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const tag = params.get('tag');
        setActiveTag(tag);
    }, []);

    const handleTagChange = (tag: string | null) => {
        setActiveTag(tag);
        const url = new URL(window.location.href);
        if (tag) {
            url.searchParams.set('tag', tag);
        } else {
            url.searchParams.delete('tag');
        }
        window.history.pushState({}, '', url.toString());
    };

    return (
        <div className="flex h-screen bg-black overflow-hidden">
            {/* Sidebar - Desktop Only */}
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
                    <SidebarItem icon={<Home size={24} />} label="For You" href="/" />
                    <SidebarItem icon={<Compass size={24} />} label="Explore" active href="/explore" />
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

            {/* Main Content */}
            <main className="flex-1 flex flex-col max-w-[1320px] w-full mx-auto overflow-x-hidden">
                {/* Category Tabs - sticky */}
                <div className="sticky top-0 z-30 bg-black/90 backdrop-blur-sm">
                    <CategoryTabs activeTag={activeTag} onTagChange={handleTagChange} />
                </div>

                {/* Grid */}
                <div className="flex-1 px-6 md:px-10 lg:px-14 xl:px-20 py-4 overflow-y-auto scrollbar-hide">
                    <ExploreGrid tag={activeTag} />
                </div>
            </main>

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
                        <button className="w-8 h-8 rounded-full bg-gradient-to-br from-[#fe2c55] to-[#25f4ee] flex items-center justify-center text-white font-bold text-xs">
                            U
                        </button>
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

            {/* Mobile Bottom Nav */}
            <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-black border-t border-gray-800/50 px-2 py-2 flex items-center justify-around">
                <a href="/" className="flex flex-col items-center gap-1 px-3 py-1 text-gray-500">
                    <Home size={24} />
                    <span className="text-[10px]">Home</span>
                </a>
                <a href="/explore" className="flex flex-col items-center gap-1 px-3 py-1 text-white">
                    <Compass size={24} />
                    <span className="text-[10px]">Discover</span>
                </a>
                <button className="p-2 bg-white rounded-lg">
                    <Upload size={24} className="text-black" />
                </button>
                <div className="flex flex-col items-center gap-1 px-3 py-1 text-gray-500">
                    <Radio size={24} />
                    <span className="text-[10px]">Inbox</span>
                </div>
                <div className="flex flex-col items-center gap-1 px-3 py-1 text-gray-500">
                    <User size={24} />
                    <span className="text-[10px]">Profile</span>
                </div>
            </nav>
        </div>
    );
};

export const ExploreApp: React.FC<ExploreAppProps> = () => {
    return (
        <AuthProvider>
            <ExploreContent />
        </AuthProvider>
    );
};
