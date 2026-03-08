/**
 * WordReel API Client
 * Connects frontend to FastAPI backend
 */

import { supabase } from './supabase';

const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ============================================================
// Types matching backend schemas
// ============================================================

export type ContentType = 'video' | 'image_slides' | 'audio' | 'quiz';
export type PostStatus = 'pending' | 'processing' | 'transcribing' | 'ready' | 'failed';

export interface WordTiming {
    word: string;
    start: number;
    end: number;
}

export interface Subtitle {
    subtitleId: string;
    templateConfig: {
        type: string;
    };
    text: string;
    startTime: number;
    endTime: number;
    wordTimings: WordTiming[];
}

export interface ImageSlide {
    url: string;
    caption?: string;
    order: number;
    altText?: string;
}

export interface QuizOption {
    id: string;
    text: string;  // API returns 'text' not 'option_text'
    is_correct: boolean;
}

export interface QuizQuestion {
    id: string;
    question: string;  // API returns 'question' not 'question_text'
    type: 'multiple_choice' | 'fill_blank' | 'arrange_sentence' | 'true_false';  // API returns 'type' not 'question_type'
    options?: QuizOption[];  // Can be null for fill_blank
    correct_answer?: string;
    explanation?: string;
    points?: number;
}

export interface Quiz {
    id: string;
    post_id: string;
    questions: QuizQuestion[];
    created_at: string;
}

export interface Post {
    id: string;
    title: string;
    description?: string;
    content_type: ContentType;
    status: PostStatus;
    duration: number;
    thumbnail_url?: string;
    tags: string[];
    difficulty_level: string;
    
    // Video fields
    video_url?: string;
    hls_url?: string;
    
    // Audio fields
    audio_url?: string;
    
    // Slides fields
    slides?: ImageSlide[];
    
    // Subtitles
    subtitles?: { subtitles: Subtitle[] }[];
    
    // Engagement
    likes_count: number;
    comments_count: number;
    views_count: number;
    shares_count: number;
    
    // User state
    is_liked: boolean;
    is_saved: boolean;
    
    created_at: string;
    updated_at: string;
}

export interface FeedResponse {
    posts: Post[];
    total: number;
    page: number;
    has_more: boolean;
}

export interface Comment {
    id: string;
    post_id: string;
    user_id: string;
    user_name: string;
    user_avatar?: string;
    content: string;
    parent_id?: string;
    likes_count: number;
    replies_count: number;
    is_liked: boolean;
    created_at: string;
}

export interface QuizResult {
    quiz_id: string;
    score: number;
    total_points: number;
    percentage: number;
    correct_answers: number;
    total_questions: number;
    passed: boolean;
    details: Array<{
        question_id: string;
        is_correct: boolean;
        user_answer: string;
        correct_answer: string;
    }>;
}

export interface User {
    id: string;
    email: string;
    username: string;
    avatar_url?: string;
    bio?: string;
    created_at: string;
}

export interface AuthToken {
    access_token: string;
    token_type: string;
    user: User;
}

// ============================================================
// API Client
// ============================================================

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
    }

    /**
     * Get a fresh access token, refreshing from Supabase if needed.
     * This ensures we always use a valid token for authenticated requests.
     */
    private async getFreshToken(): Promise<string | null> {
        if (typeof window === 'undefined') {
            return null;
        }

        // Check if we have a Supabase session and get fresh token from it
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
            // Update localStorage with the fresh token
            localStorage.setItem('wordreel_token', session.access_token);
            return session.access_token;
        }

        // Fall back to localStorage (for non-Supabase auth like email/password)
        return localStorage.getItem('wordreel_token');
    }

    /**
     * Set the auth token (used by login/register)
     */
    setToken(token: string | null): void {
        if (typeof window !== 'undefined') {
            if (token) {
                localStorage.setItem('wordreel_token', token);
            } else {
                localStorage.removeItem('wordreel_token');
            }
        }
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        // Get fresh token (auto-refreshes from Supabase if needed)
        const token = await this.getFreshToken();
        if (token) {
            (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // ========== Auth ==========
    
    async login(email: string, password: string): Promise<AuthToken> {
        const result = await this.request<AuthToken>('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setToken(result.access_token);
        return result;
    }

    async register(email: string, username: string, password: string): Promise<AuthToken> {
        const result = await this.request<AuthToken>('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password }),
        });
        this.setToken(result.access_token);
        return result;
    }

    logout(): void {
        this.setToken(null);
    }

    /**
     * Check if user is authenticated (sync check from localStorage).
     * Note: Token may be expired; actual API calls will refresh automatically.
     */
    isAuthenticated(): boolean {
        if (typeof window !== 'undefined') {
            return !!localStorage.getItem('wordreel_token');
        }
        return false;
    }

    // ========== Posts/Feed ==========

    async getFeed(
        limit = 10,
        offset = 0,
        contentType?: ContentType
    ): Promise<FeedResponse> {
        const params = new URLSearchParams({
            limit: limit.toString(),
            offset: offset.toString(),
        });
        if (contentType) {
            params.append('content_type', contentType);
        }
        return this.request<FeedResponse>(`/posts/feed?${params}`);
    }

    async getPost(postId: string): Promise<Post> {
        return this.request<Post>(`/posts/${postId}`);
    }

    async getPostsBatch(postIds: string[]): Promise<Post[]> {
        return this.request<Post[]>(`/posts/batch`, {
            method: 'POST',
            body: JSON.stringify(postIds),
        });
    }

    async likePost(postId: string): Promise<{ liked: boolean }> {
        return this.request<{ liked: boolean }>(`/posts/${postId}/like`, {
            method: 'POST',
        });
    }

    async savePost(postId: string): Promise<{ saved: boolean }> {
        return this.request<{ saved: boolean }>(`/posts/${postId}/save`, {
            method: 'POST',
        });
    }

    async recordView(
        postId: string,
        viewDuration: number,
        completed: boolean
    ): Promise<void> {
        await this.request(`/posts/${postId}/view`, {
            method: 'POST',
            body: JSON.stringify({
                view_duration: viewDuration,
                completed,
            }),
        });
    }

    // ========== Recommendations ==========

    async getRecommendations(limit = 10): Promise<FeedResponse> {
        return this.request<FeedResponse>(`/recommendations/?limit=${limit}`, {
            method: 'POST',
            body: JSON.stringify({ limit }),
        });
    }

    async getSimilarPosts(postId: string, limit = 10): Promise<Post[]> {
        return this.request<Post[]>(`/recommendations/similar/${postId}?limit=${limit}`);
    }

    // ========== Comments ==========

    async getComments(postId: string, limit = 50, offset = 0): Promise<Comment[]> {
        return this.request<Comment[]>(
            `/comments/post/${postId}?limit=${limit}&offset=${offset}`
        );
    }

    async getReplies(commentId: string, limit = 50, offset = 0): Promise<Comment[]> {
        return this.request<Comment[]>(
            `/comments/${commentId}/replies?limit=${limit}&offset=${offset}`
        );
    }

    async createComment(postId: string, content: string, parentId?: string): Promise<Comment> {
        return this.request<Comment>('/comments/', {
            method: 'POST',
            body: JSON.stringify({
                post_id: postId,
                content,
                parent_id: parentId,
            }),
        });
    }

    async deleteComment(commentId: string): Promise<void> {
        await this.request(`/comments/${commentId}`, {
            method: 'DELETE',
        });
    }

    async likeComment(commentId: string): Promise<{ liked: boolean }> {
        return this.request<{ liked: boolean }>(`/comments/${commentId}/like`, {
            method: 'POST',
        });
    }

    // ========== Quizzes ==========

    async getQuiz(postId: string): Promise<Quiz> {
        return this.request<Quiz>(`/quizzes/post/${postId}`);
    }

    async submitQuiz(
        quizId: string,
        answers: Array<{ question_id: string; selected_option_id?: string; text_answer?: string }>
    ): Promise<QuizResult> {
        return this.request<QuizResult>('/quizzes/submit', {
            method: 'POST',
            body: JSON.stringify({
                quiz_id: quizId,
                answers,
            }),
        });
    }

    async getQuizResults(postId: string): Promise<QuizResult[]> {
        return this.request<QuizResult[]>(`/quizzes/results/post/${postId}`);
    }

    // ========== Session & Recommendations ==========
    
    private sessionId: string | null = null;

    getSessionId(): string | null {
        if (!this.sessionId && typeof window !== 'undefined') {
            this.sessionId = localStorage.getItem('wordreel_session_id');
        }
        return this.sessionId;
    }

    setSessionId(sessionId: string): void {
        this.sessionId = sessionId;
        if (typeof window !== 'undefined') {
            localStorage.setItem('wordreel_session_id', sessionId);
        }
    }

    async initSession(): Promise<{ session_id: string; is_new: boolean }> {
        const existingSessionId = this.getSessionId();
        const result = await this.request<{ session_id: string; is_new: boolean }>(
            '/recommendations/session/init',
            {
                method: 'POST',
                body: JSON.stringify({
                    existing_session_id: existingSessionId || undefined,
                }),
            }
        );
        this.setSessionId(result.session_id);
        return result;
    }

    async trackWatch(
        postId: string,
        watchPercent: number,
        watchDuration: number,
        eventType: 'start' | 'progress' | 'pause' | 'finish' | 'seek' = 'progress'
    ): Promise<void> {
        const sessionId = this.getSessionId();
        if (!sessionId) return;

        await this.request('/recommendations/track', {
            method: 'POST',
            headers: {
                'X-Session-Id': sessionId,
            },
            body: JSON.stringify({
                post_id: postId,
                watch_percent: watchPercent,
                watch_duration: watchDuration,
                event_type: eventType,
            }),
        });
    }

    async getRecommendedFeed(limit = 5): Promise<FeedResponse & { prefetch_at: number }> {
        const sessionId = this.getSessionId();
        const params = new URLSearchParams({ limit: limit.toString() });
        
        const headers: HeadersInit = {};
        if (sessionId) {
            headers['X-Session-Id'] = sessionId;
        }

        return this.request<FeedResponse & { prefetch_at: number }>(
            `/recommendations/feed?${params}`,
            { headers }
        );
    }
}

// Export singleton instance
export const api = new ApiClient(API_BASE_URL);

// Export class for testing
export { ApiClient };
