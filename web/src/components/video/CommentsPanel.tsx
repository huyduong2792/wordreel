import React, { useState, useEffect } from 'react';
import { Loader2, Heart, X, ChevronUp, ChevronDown, Play } from 'lucide-react';
import { api, type Comment, type Post } from '../../lib/api';
import { useAuth } from '../auth/AuthContext';

interface CommentsPanelProps {
    postId: string;
    commentsCount: number;
    onNavigateToPost?: (postId: string) => void;
}

export const CommentsPanel: React.FC<CommentsPanelProps> = ({ postId, commentsCount, onNavigateToPost }) => {
    const { isAuthenticated, setShowAuthModal } = useAuth();
    const [comments, setComments] = useState<Comment[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [newComment, setNewComment] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [activeTab, setActiveTab] = useState<'comments' | 'related'>('comments');
    
    // Reply state
    const [replyingTo, setReplyingTo] = useState<{ id: string; name: string } | null>(null);
    const [expandedReplies, setExpandedReplies] = useState<Set<string>>(new Set());
    const [repliesMap, setRepliesMap] = useState<Record<string, Comment[]>>({});
    const [loadingReplies, setLoadingReplies] = useState<Set<string>>(new Set());
    
    // Similar posts state
    const [similarPosts, setSimilarPosts] = useState<Post[]>([]);
    const [isLoadingSimilar, setIsLoadingSimilar] = useState(false);
    const [similarPostsLoaded, setSimilarPostsLoaded] = useState(false);

    // Extract original post ID (remove _replay_... suffix if present)
    const getOriginalPostId = (id: string): string => {
        const replayIndex = id.indexOf('_replay_');
        return replayIndex !== -1 ? id.substring(0, replayIndex) : id;
    };
    
    const originalPostId = getOriginalPostId(postId);

    // Fetch comments when postId changes
    useEffect(() => {
        if (postId) {
            fetchComments();
            // Reset reply state when changing posts
            setReplyingTo(null);
            setExpandedReplies(new Set());
            setRepliesMap({});
            // Reset similar posts state
            setSimilarPosts([]);
            setSimilarPostsLoaded(false);
        }
    }, [postId]);

    // Fetch similar posts when switching to related tab
    useEffect(() => {
        if (activeTab === 'related' && originalPostId && !similarPostsLoaded) {
            fetchSimilarPosts();
        }
    }, [activeTab, originalPostId, similarPostsLoaded]);

    const fetchSimilarPosts = async () => {
        setIsLoadingSimilar(true);
        try {
            const data = await api.getSimilarPosts(originalPostId, 10);
            setSimilarPosts(data);
            setSimilarPostsLoaded(true);
        } catch (error) {
            console.error('Failed to fetch similar posts:', error);
            setSimilarPosts([]);
            setSimilarPostsLoaded(true);
        } finally {
            setIsLoadingSimilar(false);
        }
    };

    const fetchComments = async () => {
        setIsLoading(true);
        try {
            const data = await api.getComments(originalPostId);
            setComments(data);
        } catch (error) {
            console.error('Failed to fetch comments:', error);
            setComments([]);
        } finally {
            setIsLoading(false);
        }
    };

    const fetchReplies = async (commentId: string) => {
        if (loadingReplies.has(commentId)) return;
        
        setLoadingReplies(prev => new Set(prev).add(commentId));
        try {
            const replies = await api.getReplies(commentId);
            setRepliesMap(prev => ({ ...prev, [commentId]: replies }));
            setExpandedReplies(prev => new Set(prev).add(commentId));
        } catch (error) {
            console.error('Failed to fetch replies:', error);
        } finally {
            setLoadingReplies(prev => {
                const next = new Set(prev);
                next.delete(commentId);
                return next;
            });
        }
    };

    const toggleReplies = (commentId: string) => {
        if (expandedReplies.has(commentId)) {
            // Collapse
            setExpandedReplies(prev => {
                const next = new Set(prev);
                next.delete(commentId);
                return next;
            });
        } else {
            // Expand - fetch if not already loaded
            if (!repliesMap[commentId]) {
                fetchReplies(commentId);
            } else {
                setExpandedReplies(prev => new Set(prev).add(commentId));
            }
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!isAuthenticated) {
            setShowAuthModal(true);
            return;
        }
        
        if (!newComment.trim() || isSubmitting) return;

        setIsSubmitting(true);
        try {
            const comment = await api.createComment(
                originalPostId, 
                newComment.trim(), 
                replyingTo?.id
            );
            
            if (replyingTo) {
                // Add reply to the replies list
                setRepliesMap(prev => ({
                    ...prev,
                    [replyingTo.id]: [...(prev[replyingTo.id] || []), comment]
                }));
                // Update parent's replies count
                setComments(prev => prev.map(c => 
                    c.id === replyingTo.id 
                        ? { ...c, replies_count: (c.replies_count || 0) + 1 }
                        : c
                ));
                // Expand replies to show the new one
                setExpandedReplies(prev => new Set(prev).add(replyingTo.id));
                setReplyingTo(null);
            } else {
                // Add as top-level comment
                setComments(prev => [comment, ...prev]);
            }
            setNewComment('');
        } catch (error) {
            console.error('Failed to post comment:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    const formatTimeAgo = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) return `${diffDays}d ago`;
        if (diffHours > 0) return `${diffHours}h ago`;
        if (diffMins > 0) return `${diffMins}m ago`;
        return 'now';
    };

    const handleLikeComment = async (commentId: string, isReply: boolean = false, parentId?: string) => {
        if (!isAuthenticated) {
            setShowAuthModal(true);
            return;
        }

        // Find comment in either comments or replies
        let comment: Comment | undefined;
        if (isReply && parentId) {
            comment = repliesMap[parentId]?.find(c => c.id === commentId);
        } else {
            comment = comments.find(c => c.id === commentId);
        }
        if (!comment) return;

        const wasLiked = comment.is_liked;
        const previousLikesCount = comment.likes_count || 0;

        // Optimistic update
        const updateLike = (c: Comment) => {
            if (c.id === commentId) {
                return {
                    ...c,
                    is_liked: !wasLiked,
                    likes_count: wasLiked 
                        ? Math.max(previousLikesCount - 1, 0)
                        : previousLikesCount + 1
                };
            }
            return c;
        };

        if (isReply && parentId) {
            setRepliesMap(prev => ({
                ...prev,
                [parentId]: prev[parentId]?.map(updateLike) || []
            }));
        } else {
            setComments(prev => prev.map(updateLike));
        }

        // Fire and forget
        api.likeComment(commentId).catch(error => {
            console.error('Failed to like comment:', error);
            // Rollback
            const rollback = (c: Comment) => {
                if (c.id === commentId) {
                    return { ...c, is_liked: wasLiked, likes_count: previousLikesCount };
                }
                return c;
            };
            if (isReply && parentId) {
                setRepliesMap(prev => ({
                    ...prev,
                    [parentId]: prev[parentId]?.map(rollback) || []
                }));
            } else {
                setComments(prev => prev.map(rollback));
            }
        });
    };

    const handleReply = (comment: Comment) => {
        if (!isAuthenticated) {
            setShowAuthModal(true);
            return;
        }
        setReplyingTo({ id: comment.id, name: comment.user_name });
    };

    const cancelReply = () => {
        setReplyingTo(null);
        setNewComment('');
    };

    // Render a single comment item
    const renderComment = (comment: Comment, isReply: boolean = false, parentId?: string) => (
        <div key={comment.id} className={`flex gap-3 ${isReply ? 'ml-10' : ''}`}>
            {/* Avatar */}
            <div className={`${isReply ? 'w-8 h-8' : 'w-10 h-10'} rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex-shrink-0 flex items-center justify-center text-white text-sm font-bold overflow-hidden`}>
                {comment.user_avatar ? (
                    <img src={comment.user_avatar} alt="" className="w-full h-full object-cover" />
                ) : (
                    comment.user_name?.charAt(0).toUpperCase() || 'U'
                )}
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                    <span className={`font-medium ${isReply ? 'text-[12px]' : 'text-[13px]'} text-gray-300`}>
                        {comment.user_name || 'User'}
                    </span>
                </div>
                <p className={`${isReply ? 'text-[14px]' : 'text-[15px]'} text-white/90 break-words leading-snug`}>
                    {comment.content}
                </p>
                
                {/* Meta */}
                <div className="flex items-center gap-3 mt-1.5 text-[12px] text-gray-500">
                    <span>{formatTimeAgo(comment.created_at)}</span>
                    {!isReply && (
                        <button 
                            onClick={() => handleReply(comment)}
                            className="hover:text-white transition-colors"
                        >
                            Reply
                        </button>
                    )}
                </div>
                
                {/* View replies link - only for top-level comments */}
                {!isReply && (comment.replies_count ?? 0) > 0 && (
                    <button 
                        onClick={() => toggleReplies(comment.id)}
                        className="flex items-center gap-2 mt-2 text-[12px] text-gray-500 hover:text-gray-400 transition-colors"
                    >
                        {loadingReplies.has(comment.id) ? (
                            <Loader2 size={12} className="animate-spin" />
                        ) : expandedReplies.has(comment.id) ? (
                            <ChevronUp size={14} />
                        ) : (
                            <ChevronDown size={14} />
                        )}
                        <div className="w-5 h-[1px] bg-gray-600" />
                        {expandedReplies.has(comment.id) 
                            ? 'Hide replies' 
                            : `View ${comment.replies_count} ${comment.replies_count === 1 ? 'reply' : 'replies'}`
                        }
                    </button>
                )}
            </div>

            {/* Like Button */}
            <div className="flex flex-col items-center gap-0.5 pt-4">
                <button 
                    onClick={() => handleLikeComment(comment.id, isReply, parentId)}
                    className={`p-1 transition-colors ${
                        comment.is_liked 
                            ? 'text-[#fe2c55]' 
                            : 'text-gray-400 hover:text-[#fe2c55]'
                    }`}
                >
                    <Heart 
                        size={isReply ? 14 : 16} 
                        fill={comment.is_liked ? '#fe2c55' : 'none'}
                    />
                </button>
                <span className="text-[11px] text-gray-500">{comment.likes_count || 0}</span>
            </div>
        </div>
    );

    return (
        <div className="h-full flex flex-col bg-black">
            {/* Tabs - TikTok style */}
            <div className="flex border-b border-gray-800/50">
                <button
                    onClick={() => setActiveTab('comments')}
                    className={`flex-1 py-3 text-center text-[15px] font-medium transition-colors relative ${
                        activeTab === 'comments' ? 'text-white' : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                    Comments
                    {activeTab === 'comments' && (
                        <div className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-white" />
                    )}
                </button>
                <button
                    onClick={() => setActiveTab('related')}
                    className={`flex-1 py-3 text-center text-[15px] font-medium transition-colors relative ${
                        activeTab === 'related' ? 'text-white' : 'text-gray-500 hover:text-gray-300'
                    }`}
                >
                    You may like
                    {activeTab === 'related' && (
                        <div className="absolute bottom-0 left-1/4 right-1/4 h-[2px] bg-white" />
                    )}
                </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'comments' ? (
                <>
                    {/* Comment Count */}
                    <div className="px-4 py-3 text-[13px] text-gray-400">
                        {commentsCount || comments.length} comments
                    </div>

                    {/* Comments List */}
                    <div className="flex-1 overflow-y-auto px-4 space-y-5">
                        {isLoading ? (
                            <div className="flex justify-center items-center py-8">
                                <Loader2 size={24} className="animate-spin text-gray-400" />
                            </div>
                        ) : comments.length === 0 ? (
                            <div className="text-center text-gray-500 py-12">
                                <p className="text-lg mb-1">No comments yet</p>
                                <p className="text-sm">Be the first to comment!</p>
                            </div>
                        ) : (
                            comments.map((comment) => (
                                <div key={comment.id}>
                                    {/* Main comment */}
                                    {renderComment(comment)}
                                    
                                    {/* Replies */}
                                    {expandedReplies.has(comment.id) && repliesMap[comment.id] && (
                                        <div className="mt-3 space-y-3">
                                            {repliesMap[comment.id].map((reply) => 
                                                renderComment(reply, true, comment.id)
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </>
            ) : (
                /* Similar Posts / You May Like */
                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                    {isLoadingSimilar ? (
                        <div className="flex justify-center items-center py-8">
                            <Loader2 size={24} className="animate-spin text-gray-400" />
                        </div>
                    ) : similarPosts.length === 0 ? (
                        <div className="text-center text-gray-500 py-12">
                            <p className="text-lg mb-1">No recommendations yet</p>
                            <p className="text-sm">Keep watching to get personalized suggestions!</p>
                        </div>
                    ) : (
                        similarPosts.map((post) => (
                            <button
                                key={post.id}
                                onClick={() => onNavigateToPost?.(post.id)}
                                className="w-full flex gap-3 p-2 rounded-lg hover:bg-gray-800/50 transition-colors text-left group"
                            >
                                {/* Thumbnail */}
                                <div className="relative w-24 h-16 flex-shrink-0 bg-gray-800 rounded-md overflow-hidden">
                                    {post.thumbnail_url ? (
                                        <img 
                                            src={post.thumbnail_url} 
                                            alt={post.title}
                                            className="w-full h-full object-cover"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-gray-600">
                                            <Play size={20} />
                                        </div>
                                    )}
                                    {/* Duration overlay */}
                                    {post.duration > 0 && (
                                        <div className="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] px-1 py-0.5 rounded">
                                            {Math.floor(post.duration / 60)}:{(Math.floor(post.duration) % 60).toString().padStart(2, '0')}
                                        </div>
                                    )}
                                    {/* Play icon on hover */}
                                    <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <Play size={24} fill="white" className="text-white" />
                                    </div>
                                </div>
                                
                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <h4 className="text-sm text-white font-medium line-clamp-2 leading-snug">
                                        {post.title}
                                    </h4>
                                    <div className="flex items-center gap-2 mt-1.5 text-[11px] text-gray-500">
                                        <span className="capitalize">{post.difficulty_level || 'Beginner'}</span>
                                        <span>•</span>
                                        <span>{post.views_count || 0} views</span>
                                    </div>
                                    {/* Tags */}
                                    {post.tags && post.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-1.5">
                                            {post.tags.slice(0, 2).map((tag) => (
                                                <span 
                                                    key={tag}
                                                    className="text-[10px] text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded"
                                                >
                                                    #{tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </button>
                        ))
                    )}
                </div>
            )}

            {/* Input Area - TikTok style (only show on comments tab) */}
            {activeTab === 'comments' && (
                <div className="p-4 border-t border-gray-800/50">
                    {isAuthenticated ? (
                        <div>
                            {/* Reply indicator */}
                            {replyingTo && (
                                <div className="flex items-center justify-between mb-2 px-2 py-1.5 bg-[#2f2f2f] rounded-lg">
                                    <span className="text-[13px] text-gray-400">
                                        Replying to <span className="text-white">@{replyingTo.name}</span>
                                    </span>
                                    <button 
                                        onClick={cancelReply}
                                        className="p-1 hover:bg-gray-700 rounded-full transition-colors"
                                    >
                                        <X size={14} className="text-gray-400" />
                                    </button>
                                </div>
                            )}
                            <form onSubmit={handleSubmit} className="flex items-center gap-2">
                                <div className="flex-1">
                                    <input 
                                        type="text" 
                                        value={newComment}
                                        onChange={(e) => setNewComment(e.target.value)}
                                        placeholder={replyingTo ? `Reply to @${replyingTo.name}...` : "Add comment..."} 
                                        className="w-full bg-[#2f2f2f] text-white rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-gray-500 placeholder-gray-500"
                                        disabled={isSubmitting}
                                        autoFocus={!!replyingTo}
                                    />
                                </div>
                                <button
                                    type="submit"
                                    disabled={!newComment.trim() || isSubmitting}
                                    className="px-4 py-2.5 text-[#fe2c55] hover:text-[#ff5c7c] disabled:text-gray-600 disabled:cursor-not-allowed transition-colors font-semibold text-sm"
                                >
                                    {isSubmitting ? (
                                        <Loader2 size={18} className="animate-spin" />
                                    ) : (
                                        'Post'
                                    )}
                                </button>
                            </form>
                        </div>
                    ) : (
                        <button
                            onClick={() => setShowAuthModal(true)}
                            className="w-full py-3 text-center text-[#fe2c55] hover:bg-[#fe2c55]/10 rounded-lg transition-colors font-semibold text-sm"
                        >
                            Log in to comment
                        </button>
                    )}
                </div>
            )}
        </div>
    );
};
