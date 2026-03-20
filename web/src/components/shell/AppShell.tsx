import React from 'react';
import { useAuth, AuthModal, UserMenu } from '../auth';
import { SidebarNav } from './SidebarNav';
import { BottomNav } from './BottomNav';

export interface AppShellProps {
    activeNavItem: 'home' | 'explore';
    showRightPanel?: boolean;
    renderContentHeader?: () => React.ReactNode;
    renderTopRight?: () => React.ReactNode;
    children?: React.ReactNode;
    renderRightPanel?: () => React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
    activeNavItem,
    showRightPanel = false,
    renderContentHeader,
    renderTopRight,
    children,
    renderRightPanel,
}) => {
    const { showAuthModal, setShowAuthModal, isAuthenticated } = useAuth();

    return (
        <div className="flex h-screen bg-black overflow-hidden">
            <SidebarNav activeItem={activeNavItem} />

            <main className={`flex-1 flex ${showRightPanel ? 'justify-center' : ''} overflow-hidden`}>
                <div className={`w-full ${showRightPanel ? 'max-w-[600px]' : ''} h-full`}>
                    {renderContentHeader && (
                        <div className="sticky top-0 z-30 bg-black/90 backdrop-blur-sm">
                            <div className="flex items-center">
                                <div className="flex-1 min-w-0">
                                    {renderContentHeader()}
                                </div>
                                {!showRightPanel && (
                                    <div className="flex items-center gap-2 px-4 flex-shrink-0">
                                        {renderTopRight ? renderTopRight() : (
                                            isAuthenticated ? <UserMenu /> : (
                                                <button
                                                    onClick={() => setShowAuthModal(true)}
                                                    className="px-4 py-1.5 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-semibold rounded-md transition-colors text-sm"
                                                >
                                                    Log in
                                                </button>
                                            )
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                    <div className="h-[calc(100%-0px)] overflow-y-auto scrollbar-hide">
                        {children}
                    </div>
                </div>
            </main>

            {showRightPanel && renderRightPanel && (
                <>
                    {/* Navigation Arrows */}
                    <div className="hidden lg:flex fixed right-[420px] top-1/2 -translate-y-1/2 flex-col gap-3 z-50">
                        <button className="w-12 h-12 bg-[#2f2f2f] hover:bg-[#3f3f3f] rounded-full flex items-center justify-center transition-colors">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white"><polyline points="18 15 12 9 6 15"></polyline></svg>
                        </button>
                        <button className="w-12 h-12 bg-[#2f2f2f] hover:bg-[#3f3f3f] rounded-full flex items-center justify-center transition-colors">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white"><polyline points="6 9 12 15 18 9"></polyline></svg>
                        </button>
                    </div>

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

                        {/* Right Panel Content */}
                        <div className="flex-1 overflow-hidden">
                            {renderRightPanel()}
                        </div>
                    </div>
                </>
            )}

            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-black/90 backdrop-blur-sm">
                <div className="flex items-center justify-between px-4 py-3">
                    <a href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#fe2c55] to-[#25f4ee] flex items-center justify-center">
                            <span className="text-white font-bold">W</span>
                        </div>
                        <span className="font-bold text-white">WordReel</span>
                    </a>

                    {renderTopRight ? renderTopRight() : (
                        isAuthenticated ? (
                            <UserMenu />
                        ) : (
                            <button
                                onClick={() => setShowAuthModal(true)}
                                className="px-4 py-2 bg-[#fe2c55] hover:bg-[#ef2950] text-white font-bold rounded-md transition-colors text-sm"
                            >
                                Log in
                            </button>
                        )
                    )}
                </div>
            </header>

            <BottomNav activeItem={activeNavItem} isAuthenticated={isAuthenticated} onAuthClick={() => setShowAuthModal(true)} />

            <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
        </div>
    );
};
