import React, { useState, useRef, useEffect, useCallback } from 'react';
import { VideoPlayer } from './VideoPlayer';
import { AudioPlayer } from './AudioPlayer';
import { SlidesPlayer } from './SlidesPlayer';
import { VideoControls } from './VideoControls';
import { ShareModal } from './ShareModal';
import { api } from '../../lib/api';
import { postToVideoData, MOCK_VIDEO } from './types';
import type { VideoData, ContentType } from './types';
import { useAuth } from '../auth/AuthContext';

export interface VideoControlsState {
    showSubtitles: boolean;
    playbackSpeed: number;
    onToggleSubtitles: () => void;
    onChangeSpeed: (speed?: number) => void;
}

export interface ActivePostData {
    postId: string;
    likes: number;
    comments: number;
    shares: number;
    isLiked: boolean;
    isSaved: boolean;
    onToggleLike: () => void;
    onToggleSave: () => void;
}

interface VideoFeedProps {
    contentType?: ContentType;
    onActivePostChange?: (postId: string, commentsCount: number) => void;
    onActivePostDataChange?: (data: ActivePostData | null) => void;
    onControlsStateChange?: (state: VideoControlsState | null) => void;
    initialPostId?: string;
    sessionReady?: boolean;
}

export const VideoFeed: React.FC<VideoFeedProps> = ({ contentType, onActivePostChange, onActivePostDataChange, onControlsStateChange, initialPostId, sessionReady = false }) => {
    const { isAuthenticated, setShowAuthModal } = useAuth();
    const [posts, setPosts] = useState<VideoData[]>([]);
    const [activeIndex, setActiveIndex] = useState(0);
    // Restore mute preference from localStorage (default to true for autoplay)
    const [isMuted, setIsMuted] = useState(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('wordreel_muted');
            return saved !== 'false'; // Default to true if not set
        }
        return true;
    });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [hasMore, setHasMore] = useState(true);
    const [initialLoadDone, setInitialLoadDone] = useState(false);
    
    // Share modal state
    const [shareModalOpen, setShareModalOpen] = useState(false);
    const [sharePostId, setSharePostId] = useState<string>('');
    
    // Video controls state (lifted up from VideoPlayer)
    const [showSubtitles, setShowSubtitles] = useState(true);
    const [playbackSpeed, setPlaybackSpeed] = useState(1);
    
    // Persist mute preference
    const handleMuteChange = useCallback((muted: boolean) => {
        setIsMuted(muted);
        localStorage.setItem('wordreel_muted', String(muted));
    }, []);
    
    // Handle speed change
    const handleChangeSpeed = useCallback((speed?: number) => {
        if (speed !== undefined) {
            setPlaybackSpeed(speed);
        } else {
            // Toggle between 0.5 and 1
            setPlaybackSpeed(prev => prev === 1 ? 0.5 : 1);
        }
    }, []);
    
    const containerRef = useRef<HTMLDivElement>(null);
    const videoRefs = useRef<Map<string, HTMLDivElement>>(new Map());
    const loadingRef = useRef(false);
    const prefetchTriggeredRef = useRef(false);

    // Notify parent when active post changes
    useEffect(() => {
        if (posts.length > 0 && posts[activeIndex]) {
            const post = posts[activeIndex];
            onActivePostChange?.(post.id, post.comments);
            
            // Notify parent of full active post data for external controls
            onActivePostDataChange?.({
                postId: post.originalId || post.id,
                likes: post.likes,
                comments: post.comments,
                shares: post.shares,
                isLiked: post.isLiked,
                isSaved: post.isSaved,
                onToggleLike: () => handleLike(post.originalId || post.id),
                onToggleSave: () => handleSave(post.originalId || post.id),
            });
        } else {
            onActivePostDataChange?.(null);
        }
    }, [activeIndex, posts, onActivePostChange, onActivePostDataChange]);
    
    // Notify parent of controls state changes
    useEffect(() => {
        onControlsStateChange?.({
            showSubtitles,
            playbackSpeed,
            onToggleSubtitles: () => setShowSubtitles(prev => !prev),
            onChangeSpeed: handleChangeSpeed,
        });
    }, [showSubtitles, playbackSpeed, onControlsStateChange, handleChangeSpeed]);

    // Fetch posts using recommendation feed (for appending more posts)
    const fetchPosts = useCallback(async (append = false) => {
        if (loadingRef.current) return;
        loadingRef.current = true;
        
        try {
            setIsLoading(true);
            
            // Use recommendation feed API (returns 5 posts)
            const response = await api.getRecommendedFeed(5);
            
            const videoData = response.posts.map(postToVideoData);
            
            if (append) {
                // When appending, allow duplicates (for replay when user watched all videos)
                // But avoid adding the exact same sequence if user is just scrolling back
                setPosts(prev => {
                    // Check if these are all duplicates of recent posts (not replay scenario)
                    const lastFiveIds = new Set(prev.slice(-5).map(p => p.id));
                    const allDuplicatesOfRecent = videoData.every(p => lastFiveIds.has(p.id));
                    
                    if (allDuplicatesOfRecent && videoData.length > 0) {
                        // This might be replay - allow duplicates to enable infinite scroll
                        // Add with a unique key suffix to differentiate
                        const replayPosts = videoData.map((p, i) => ({
                            ...p,
                            id: `${p.id}_replay_${Date.now()}_${i}`, // Unique ID for React key
                            originalId: p.id // Keep original for tracking
                        }));
                        return [...prev, ...replayPosts];
                    }
                    
                    // Normal case: filter out duplicates
                    const existingIds = new Set(prev.map(p => p.id));
                    const newPosts = videoData.filter(p => !existingIds.has(p.id));
                    
                    // If no new posts but has_more is true, it's replay scenario
                    if (newPosts.length === 0 && response.has_more) {
                        const replayPosts = videoData.map((p, i) => ({
                            ...p,
                            id: `${p.id}_replay_${Date.now()}_${i}`,
                            originalId: p.id
                        }));
                        return [...prev, ...replayPosts];
                    }
                    
                    return [...prev, ...newPosts];
                });
            } else {
                setPosts(videoData);
            }
            
            setHasMore(response.has_more);
            setError(null);
            prefetchTriggeredRef.current = false; // Reset prefetch trigger
        } catch (err) {
            console.error('Failed to fetch feed:', err);
            setError('Failed to load content');
            
            // Fallback to mock data in development
            if (!append && posts.length === 0) {
                setPosts([MOCK_VIDEO]);
            }
        } finally {
            setIsLoading(false);
            loadingRef.current = false;
        }
    }, [contentType]);

    // Initial load when session is ready
    useEffect(() => {
        if (!sessionReady || initialLoadDone) return;
        
        const loadInitialFeed = async () => {
            if (loadingRef.current) return;
            loadingRef.current = true;
            setIsLoading(true);
            
            try {
                let initialPosts: VideoData[] = [];
                
                // If initialPostId, fetch that post first
                if (initialPostId) {
                    try {
                        const targetPost = await api.getPost(initialPostId);
                        initialPosts = [postToVideoData(targetPost)];
                    } catch (err) {
                        console.error('Failed to fetch initial post:', err);
                    }
                }
                
                // Then load normal feed
                const response = await api.getRecommendedFeed(5);
                const feedData = response.posts.map(postToVideoData);
                
                if (initialPosts.length > 0) {
                    // Prepend initial post, then add feed posts (excluding duplicates)
                    const existingIds = new Set(initialPosts.map(p => p.id));
                    const newPosts = feedData.filter(p => !existingIds.has(p.id));
                    setPosts([...initialPosts, ...newPosts]);
                } else {
                    setPosts(feedData);
                }
                
                setHasMore(response.has_more);
                setError(null);
                setActiveIndex(0);
            } catch (err) {
                console.error('Failed to load feed:', err);
                setError('Failed to load content');
                setPosts([MOCK_VIDEO]);
            } finally {
                setIsLoading(false);
                loadingRef.current = false;
                setInitialLoadDone(true);
            }
        };
        
        loadInitialFeed();
    }, [sessionReady, initialPostId, initialLoadDone]);

    // Prefetch when less than 2 videos remaining to play
    // Only run AFTER initial load is complete
    useEffect(() => {
        if (!initialLoadDone) return; // Wait for initial load first!
        
        const remainingVideos = posts.length - activeIndex - 1;
        if (remainingVideos < 2 && hasMore && !prefetchTriggeredRef.current && !loadingRef.current) {
            prefetchTriggeredRef.current = true;
            fetchPosts(true);
        }
    }, [activeIndex, posts.length, hasMore, fetchPosts, initialLoadDone]);

    // Use IntersectionObserver for reliable active video detection
    useEffect(() => {
        const container = containerRef.current;
        if (!container || posts.length === 0) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
                        const postId = entry.target.getAttribute('data-post-id');
                        const index = posts.findIndex(p => p.id === postId);
                        if (index !== -1 && index !== activeIndex) {
                            setActiveIndex(index);
                        }
                    }
                });
            },
            {
                root: container,
                threshold: [0.6], // Trigger when 60% visible
            }
        );

        // Observe all video containers
        videoRefs.current.forEach((element) => {
            observer.observe(element);
        });

        return () => {
            observer.disconnect();
        };
    }, [posts, activeIndex]);

    // Store ref for each video container
    const setVideoRef = useCallback((postId: string, element: HTMLDivElement | null) => {
        if (element) {
            videoRefs.current.set(postId, element);
        } else {
            videoRefs.current.delete(postId);
        }
    }, []);

    // Handle like action (optimistic update)
    const handleLike = async (postId: string) => {
        // Require login for like
        if (!isAuthenticated) {
            setShowAuthModal(true);
            return;
        }
        
        // Find current state for this post
        const currentPost = posts.find(p => (p.originalId || p.id) === postId);
        if (!currentPost) return;
        
        const wasLiked = currentPost.isLiked;
        
        // Optimistic update - immediately toggle UI
        setPosts(prev => prev.map(post => 
            (post.originalId || post.id) === postId 
                ? { 
                    ...post, 
                    isLiked: !wasLiked,
                    likes: wasLiked ? post.likes - 1 : post.likes + 1
                }
                : post
        ));
        
        try {
            const result = await api.likePost(postId);
            
            // Sync with server response (in case of mismatch)
            setPosts(prev => prev.map(post => 
                (post.originalId || post.id) === postId 
                    ? { 
                        ...post, 
                        isLiked: result.liked,
                        likes: result.liked ? currentPost.likes + 1 : currentPost.likes - 1
                    }
                    : post
            ));
        } catch (err) {
            console.error('Failed to like post:', err);
            // Revert on error
            setPosts(prev => prev.map(post => 
                (post.originalId || post.id) === postId 
                    ? { 
                        ...post, 
                        isLiked: wasLiked,
                        likes: currentPost.likes
                    }
                    : post
            ));
        }
    };

    // Handle save action (optimistic update)
    const handleSave = async (postId: string) => {
        // Require login for save
        if (!isAuthenticated) {
            setShowAuthModal(true);
            return;
        }
        
        // Find current state for this post
        const currentPost = posts.find(p => (p.originalId || p.id) === postId);
        if (!currentPost) return;
        
        const wasSaved = currentPost.isSaved;
        
        // Optimistic update - immediately toggle UI
        setPosts(prev => prev.map(post => 
            (post.originalId || post.id) === postId 
                ? { ...post, isSaved: !wasSaved }
                : post
        ));
        
        try {
            const result = await api.savePost(postId);
            
            // Sync with server response (in case of mismatch)
            setPosts(prev => prev.map(post => 
                (post.originalId || post.id) === postId 
                    ? { ...post, isSaved: result.saved }
                    : post
            ));
        } catch (err) {
            console.error('Failed to save post:', err);
            // Revert on error
            setPosts(prev => prev.map(post => 
                (post.originalId || post.id) === postId 
                    ? { ...post, isSaved: wasSaved }
                    : post
            ));
        }
    };

    // Handle share action
    const handleShare = (postId: string) => {
        setSharePostId(postId);
        setShareModalOpen(true);
    };

    // Render appropriate player based on content type
    const renderPlayer = (post: VideoData, index: number) => {
        const isActive = index === activeIndex;
        const commonProps = {
            data: post,
            isActive,
            isMuted,
            onMuteChange: handleMuteChange,
            onLike: () => handleLike(post.originalId || post.id),
            onSave: () => handleSave(post.originalId || post.id),
            showSubtitles,
            playbackSpeed,
        };

        switch (post.contentType) {
            case 'audio':
                return <AudioPlayer {...commonProps} />;
            case 'image_slides':
                return <SlidesPlayer {...commonProps} />;
            case 'video':
            default:
                return <VideoPlayer {...commonProps} />;
        }
    };

    if (isLoading && posts.length === 0) {
        return (
            <div className="h-full w-full flex items-center justify-center bg-black">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-gray-400">Loading content...</p>
                </div>
            </div>
        );
    }

    if (error && posts.length === 0) {
        return (
            <div className="h-full w-full flex items-center justify-center bg-black">
                <div className="flex flex-col items-center gap-4 text-center px-8">
                    <p className="text-red-400">{error}</p>
                    <button 
                        onClick={() => fetchPosts(false)}
                        className="px-6 py-2 bg-blue-600 text-white rounded-full hover:bg-blue-700"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div 
            ref={containerRef}
            className="h-full w-full overflow-y-scroll snap-y snap-mandatory scrollbar-hide flex flex-col items-center"
            style={{ scrollBehavior: 'smooth' }}
        >
            {posts.map((post, index) => (
                <div 
                    key={post.id} 
                    ref={(el) => setVideoRef(post.id, el)}
                    data-post-id={post.id}
                    className="h-full w-auto flex-shrink-0 snap-start snap-always relative flex items-center justify-center p-3"
                >
                    <div className="h-full flex items-end gap-3">
                        {/* Video Player */}
                        <div className="h-full aspect-[9/16] max-w-full rounded-xl overflow-hidden">
                            {renderPlayer(post, index)}
                        </div>
                        
                        {/* Action Buttons - Bottom right of video */}
                        <div className="hidden lg:flex pb-4">
                            <VideoControls
                                likes={post.likes}
                                shares={post.shares}
                                isLiked={post.isLiked}
                                isSaved={post.isSaved}
                                showSubtitles={showSubtitles}
                                playbackSpeed={playbackSpeed}
                                onToggleLike={() => handleLike(post.originalId || post.id)}
                                onToggleSave={() => handleSave(post.originalId || post.id)}
                                onToggleSubtitles={() => setShowSubtitles(prev => !prev)}
                                onChangeSpeed={handleChangeSpeed}
                                onShare={() => handleShare(post.originalId || post.id)}
                            />
                        </div>
                    </div>
                </div>
            ))}
            
            {/* Loading indicator at bottom */}
            {isLoading && posts.length > 0 && (
                <div className="h-20 flex items-center justify-center">
                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
            )}
            
            {/* Share Modal */}
            <ShareModal 
                isOpen={shareModalOpen}
                onClose={() => setShareModalOpen(false)}
                postId={sharePostId}
            />
        </div>
    );
};
