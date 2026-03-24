import React from 'react';
import { Heart } from 'lucide-react';
import type { Post } from '../../lib/api';
import { formatCount } from '../../lib/utils';

interface PostCardProps {
    post: Post;
}

const GRADIENT_FALLBACKS = [
    'from-[#fe2c55] to-[#25f4ee]',
    'from-[#00f2ea] to-[#ff0050]',
    'from-[#7b2ff7] to-[#f72fff]',
    'from-[#f9ca24] to-[#f0932b]',
    'from-[#00b894] to-[#0984e3]',
];

function getGradient(index: number): string {
    return GRADIENT_FALLBACKS[index % GRADIENT_FALLBACKS.length];
}

export const PostCard: React.FC<PostCardProps> = ({ post }) => {
    const gradientIdx = Math.abs(post.id.charCodeAt(0) + post.id.charCodeAt(1)) % GRADIENT_FALLBACKS.length;

    return (
        <a href={`/post/${post.id}`} className="block group cursor-pointer">
            {/* Thumbnail - 9:16 portrait */}
            <div className="relative w-full aspect-[9/16] overflow-hidden rounded-lg bg-[#1a1a1a]">
                {post.thumbnail_url ? (
                    <img
                        src={post.thumbnail_url}
                        alt={post.title}
                        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                ) : (
                    <div className={`w-full h-full bg-gradient-to-br ${getGradient(gradientIdx)}`} />
                )}

                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="w-10 h-10 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center">
                        <svg viewBox="0 0 24 24" className="w-4 h-4 text-white ml-0.5" fill="white">
                            <path d="M8 5v14l11-7z" />
                        </svg>
                    </div>
                </div>

                {/* Like count - bottom right */}
                <div className="absolute bottom-1.5 right-1.5 flex items-center gap-0.5 text-white text-xs font-medium drop-shadow-sm">
                    <Heart size={11} fill="white" />
                    <span>{formatCount(post.likes_count)}</span>
                </div>
            </div>

            {/* Username below thumbnail */}
            {post.creator_name ? (
                <p className="mt-1.5 text-gray-300 text-xs truncate">
                    @{post.creator_name}
                </p>
            ) : post.username ? (
                <p className="mt-1.5 text-gray-300 text-xs truncate">
                    @{post.username}
                </p>
            ) : null}
        </a>
    );
};

// Skeleton placeholder
export const PostCardSkeleton: React.FC = () => {
    return (
        <div className="animate-pulse">
            <div className="w-full aspect-[9/16] rounded-lg bg-[#2a2a2a]" />
            <div className="mt-1.5 h-3 bg-[#2a2a2a] rounded w-2/3" />
        </div>
    );
};
