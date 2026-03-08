/**
 * Video/Post Types - Frontend types matching backend API
 */
import type { Post, Subtitle, WordTiming, ContentType, Quiz, QuizQuestion } from '../../lib/api';

// Re-export from API for convenience
export type { Post, Subtitle, WordTiming, ContentType, Quiz, QuizQuestion };

// Legacy VideoData interface (mapped from Post for backward compatibility)
export interface VideoData {
    id: string;
    originalId?: string; // Original post ID when replayed (id becomes unique for React key)
    url: string;
    hlsUrl?: string;
    thumbnailUrl?: string;
    username: string;
    title: string;
    description: string;
    likes: number;
    comments: number;
    shares: number;
    views: number;
    isLiked: boolean;
    isSaved: boolean;
    subtitles: SubtitleDisplay[];
    contentType: ContentType;
    // Audio-specific
    audioUrl?: string;
    // Slides-specific
    slides?: Array<{
        url: string;
        caption?: string;
        order: number;
    }>;
    // Quiz
    hasQuiz?: boolean;
}

// Simplified subtitle for display (transformed from API format)
export interface SubtitleDisplay {
    id: string;
    text: string;
    startTime: number;
    endTime: number;
    wordTimings?: WordTiming[];
}

export interface Comment {
    id: string;
    username: string;
    text: string;
    avatar?: string;
    likes: number;
    timestamp: string;
    isLiked: boolean;
}

/**
 * Transform backend Post to frontend VideoData
 */
export function postToVideoData(post: Post): VideoData {
    // Extract subtitles - handle both flat and nested structures
    const subtitles: SubtitleDisplay[] = [];
    if (post.subtitles && post.subtitles.length > 0) {
        // Check if it's nested structure (post.subtitles[0].subtitles) or flat (post.subtitles[])
        const firstItem = post.subtitles[0] as any;
        const subtitleData = firstItem?.subtitles 
            ? firstItem.subtitles  // Nested structure
            : post.subtitles;      // Flat structure
        
        for (const sub of subtitleData) {
            subtitles.push({
                id: sub.subtitleId,
                text: sub.text,
                startTime: sub.startTime,
                endTime: sub.endTime,
                wordTimings: sub.wordTimings,
            });
        }
    }

    return {
        id: post.id,
        url: post.video_url || post.audio_url || '',
        hlsUrl: post.hls_url,
        thumbnailUrl: post.thumbnail_url,
        username: '@user', // TODO: fetch user info separately
        title: post.title,
        description: post.description || '',
        likes: post.likes_count,
        comments: post.comments_count,
        shares: post.shares_count,
        views: post.views_count,
        isLiked: post.is_liked,
        isSaved: post.is_saved,
        subtitles,
        contentType: post.content_type,
        audioUrl: post.audio_url,
        slides: post.slides,
        hasQuiz: true, // We can check this via API
    };
}

// Mock data for development/fallback
export const MOCK_VIDEO: VideoData = {
    id: "mock-1",
    url: "https://ps.mediacdn.vn/.hls/huydq/workreel_demo1.mp4.master.m3u8",
    username: "@english_learner",
    title: "Learning English",
    description: "Learning colors in neon lights! 🌈 #english #learning",
    likes: 12400,
    comments: 342,
    shares: 105,
    views: 50000,
    isLiked: false,
    isSaved: false,
    contentType: 'video',
    subtitles: [
        {
            id: "s1",
            text: "Welcome to the neon city lights",
            startTime: 1.0,
            endTime: 3.0,
            wordTimings: [
                { word: "Welcome", start: 1.0, end: 1.4 },
                { word: "to", start: 1.4, end: 1.6 },
                { word: "the", start: 1.6, end: 1.8 },
                { word: "neon", start: 1.8, end: 2.2 },
                { word: "city", start: 2.2, end: 2.6 },
                { word: "lights", start: 2.6, end: 3.0 }
            ]
        },
        {
            id: "s2",
            text: "Where everything shines bright",
            startTime: 3.2,
            endTime: 5.0,
            wordTimings: [
                { word: "Where", start: 3.2, end: 3.5 },
                { word: "everything", start: 3.5, end: 4.2 },
                { word: "shines", start: 4.2, end: 4.6 },
                { word: "bright", start: 4.6, end: 5.0 }
            ]
        }
    ]
};
