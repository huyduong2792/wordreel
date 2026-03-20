import React from 'react';

const CATEGORIES = [
    { label: 'Tất cả', tag: null },
    { label: 'Singing & Dancing', tag: 'singing-dancing' },
    { label: 'Entertainment', tag: 'entertainment' },
    { label: 'Sports', tag: 'sports' },
    { label: 'Comics & Animation', tag: 'comics-animation' },
    { label: 'News', tag: 'news' },
    { label: 'Learning', tag: 'learning' },
    { label: 'Cooking', tag: 'cooking' },
];

interface CategoryTabsProps {
    activeTag: string | null;
    onTagChange: (tag: string | null) => void;
}

export const CategoryTabs: React.FC<CategoryTabsProps> = ({ activeTag, onTagChange }) => {
    return (
        <div className="overflow-x-auto scrollbar-hide min-w-0">
            <div className="flex items-center gap-2 px-6 md:px-10 lg:px-14 xl:px-20 py-6">
                {CATEGORIES.map((cat) => {
                    const isActive = cat.tag === activeTag;
                    return (
                        <button
                            key={cat.tag ?? 'all'}
                            onClick={() => onTagChange(cat.tag)}
                            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap ${
                                isActive
                                    ? 'bg-white text-black'
                                    : 'text-gray-400 hover:text-white hover:bg-white/10'
                            }`}
                        >
                            {cat.label}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};
