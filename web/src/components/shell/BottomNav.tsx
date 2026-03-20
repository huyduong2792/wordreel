import React from 'react';
import { Home, Compass, Upload, Radio, User } from 'lucide-react';

interface BottomNavItemProps {
    icon: React.ReactNode;
    label: string;
    active?: boolean;
    href?: string;
    onClick?: () => void;
}

export const BottomNavItem: React.FC<BottomNavItemProps> = ({ icon, label, active, href, onClick }) =>
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

interface BottomNavProps {
    activeItem: 'home' | 'explore';
    isAuthenticated: boolean;
    onAuthClick?: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeItem, isAuthenticated, onAuthClick }) => {
    return (
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-black border-t border-gray-800/50 px-2 py-2 flex items-center justify-around">
            <BottomNavItem icon={<Home size={24} />} label="Home" active={activeItem === 'home'} href="/" />
            <BottomNavItem icon={<Compass size={24} />} label="Discover" active={activeItem === 'explore'} href="/explore" />
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
                onClick={() => !isAuthenticated && onAuthClick?.()}
            />
        </nav>
    );
};
