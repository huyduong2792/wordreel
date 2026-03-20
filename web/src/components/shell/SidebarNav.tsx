import React from 'react';
import { Home, Compass, Search } from 'lucide-react';
import { useAuth } from '../auth';

interface SidebarItemProps {
    icon: React.ReactNode;
    label: string;
    active?: boolean;
    href?: string;
}

export const SidebarItem: React.FC<SidebarItemProps> = ({ icon, label, active, href }) =>
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

interface SidebarNavProps {
    activeItem: 'home' | 'explore';
}

export const SidebarNav: React.FC<SidebarNavProps> = ({ activeItem }) => {
    const { showAuthModal, setShowAuthModal, isAuthenticated } = useAuth();

    return (
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
                <SidebarItem icon={<Home size={24} />} label="For You" active={activeItem === 'home'} href="/" />
                <SidebarItem icon={<Compass size={24} />} label="Explore" active={activeItem === 'explore'} href="/explore" />
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
    );
};
