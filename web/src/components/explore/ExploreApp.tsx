import React, { useState, useEffect } from 'react';
import { AuthProvider, UserMenu } from '../auth';
import { CategoryTabs } from './CategoryTabs';
import { ExploreGrid } from './ExploreGrid';
import { AppShell } from '../shell';

interface ExploreContentProps {}

const ExploreContent: React.FC<ExploreContentProps> = () => {
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
        <AppShell
            activeNavItem="explore"
            renderContentHeader={() => (
                <CategoryTabs activeTag={activeTag} onTagChange={handleTagChange} />
            )}
            renderTopRight={() => <UserMenu />}
        >
            <div className="flex-1 px-6 md:px-10 lg:px-14 xl:px-20 overflow-y-auto scrollbar-hide">
                <ExploreGrid tag={activeTag} />
            </div>
        </AppShell>
    );
};

interface ExploreAppProps {}

export const ExploreApp: React.FC<ExploreAppProps> = () => {
    return (
        <AuthProvider>
            <ExploreContent />
        </AuthProvider>
    );
};
