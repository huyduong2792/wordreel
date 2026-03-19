import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PostCard, PostCardSkeleton } from './PostCard';
import { api } from '../../lib/api';
import type { Post } from '../../lib/api';
import { MOCK_POSTS } from '../../lib/mockExploreData';

const USE_MOCK = true; // Toggle to false when real API is ready

interface ExploreGridProps {
    tag: string | null;
}

function filterByTag(posts: Post[], tag: string | null): Post[] {
    if (!tag) return posts;
    return posts.filter((p) => p.tags.includes(tag));
}

export const ExploreGrid: React.FC<ExploreGridProps> = ({ tag }) => {
    const [posts, setPosts] = useState<Post[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [offset, setOffset] = useState(0);
    const sentinelRef = useRef<HTMLDivElement>(null);
    const LIMIT = 20;

    const fetchPosts = useCallback(async (pageOffset: number, append: boolean) => {
        if (append) {
            setLoadingMore(true);
        } else {
            setLoading(true);
        }
        try {
            let newPosts: Post[] = [];

            if (USE_MOCK) {
                const filtered = filterByTag(MOCK_POSTS, tag);
                newPosts = filtered.slice(pageOffset, pageOffset + LIMIT);
                setHasMore(pageOffset + LIMIT < filtered.length);
            } else {
                const response = await api.getExploreFeed(LIMIT, pageOffset, tag ?? undefined);
                newPosts = response.posts;
                setHasMore(response.has_more);
            }

            if (append) {
                setPosts((prev) => [...prev, ...newPosts]);
            } else {
                setPosts(newPosts);
            }
            setOffset(pageOffset + newPosts.length);
        } catch (err) {
            console.error('Failed to fetch explore feed:', err);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [tag]);

    // Initial fetch when tag changes
    useEffect(() => {
        setPosts([]);
        setOffset(0);
        setHasMore(true);
        fetchPosts(0, false);
    }, [tag, fetchPosts]);

    // IntersectionObserver for infinite scroll
    useEffect(() => {
        const sentinel = sentinelRef.current;
        if (!sentinel) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore && !loadingMore && !loading) {
                    fetchPosts(offset, true);
                }
            },
            { rootMargin: '200px' }
        );

        observer.observe(sentinel);
        return () => observer.disconnect();
    }, [hasMore, loadingMore, loading, offset, fetchPosts]);

    if (loading) {
        return (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-x-5 gap-y-5">
                {Array.from({ length: 10 }).map((_, i) => (
                    <PostCardSkeleton key={i} />
                ))}
            </div>
        );
    }

    if (posts.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                <p>No posts found</p>
            </div>
        );
    }

    return (
        <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-x-5 gap-y-5">
                {posts.map((post) => (
                    <PostCard key={post.id} post={post} />
                ))}
            </div>

            {/* Sentinel for infinite scroll */}
            <div ref={sentinelRef} className="flex justify-center py-4">
                {loadingMore && (
                    <div className="w-6 h-6 border-2 border-gray-600 border-t-white rounded-full animate-spin" />
                )}
            </div>
        </>
    );
};
