---
applyTo: "web/**"
description: "Frontend patterns for React, Astro, and TypeScript components"
---

# Frontend Development Guide

## Critical: React Hooks Order

**All hooks MUST be called before any conditional returns:**

```typescript
// ✅ CORRECT: Hooks at top
const Component = ({ isVisible, data }: Props) => {
    const [state, setState] = useState(initial);
    const computed = useMemo(() => process(data), [data]);
    
    // Conditional returns AFTER hooks
    if (!isVisible) return null;
    
    return <div>...</div>;
};

// ❌ WRONG: Hook after conditional - CRASHES!
const Component = ({ isVisible }) => {
    if (!isVisible) return null;  // BAD!
    const [state, setState] = useState();  // "Rendered fewer hooks" error
};
```

---

## Code Standards

| Rule | Description |
|------|-------------|
| **Hooks at Top** | ALL React hooks before any conditional returns |
| **TypeScript** | Use proper interfaces for props and state |
| **API Client** | Use `api.ts` for all backend calls |
| **Error Boundaries** | Handle errors gracefully with user feedback |
| **TailwindCSS** | Use Tailwind utilities, avoid inline styles |

---

## Key Components

### VideoPlayer (`components/video/VideoPlayer.tsx`)

Main player with streaming support:

```typescript
interface VideoPlayerProps {
    data: VideoData;
    isActive: boolean;      // Controls autoplay
    isMuted: boolean;       // Global mute state
    onMuteChange: (muted: boolean) => void;
}
```

**Video Source Priority:** DASH → HLS → Direct URL

```typescript
const initPlayer = async () => {
    if (data.dashUrl) {
        await initDash(data.dashUrl);  // dash.js
    } else if (data.hlsUrl) {
        initHls(data.hlsUrl);           // hls.js
    } else if (data.url) {
        video.src = data.url;           // Native fallback
    }
};
```

**Critical: Cleanup to prevent audio overlap:**
```typescript
useEffect(() => {
    if (isActive) {
        const timeout = setTimeout(() => video.play(), 50);
        return () => {
            clearTimeout(timeout);
            video.pause();
            video.currentTime = 0;
        };
    }
}, [isActive]);
```

### SubtitleOverlay (`components/video/SubtitleOverlay.tsx`)

Karaoke-style word highlighting:

```typescript
// Word states
const isHighlighted = currentTime >= word.start && currentTime <= word.end;
const isPast = currentTime > word.end;

// CSS applied:
// isHighlighted: text-yellow-400 font-extrabold + glow
// isPast: text-white/90
// Future: text-white/60
```

**Layout rules:**
- Position: `bottom-32 left-4 right-20` (avoids controls)
- Max 6 words per line for readability

### VideoQuiz (`components/video/VideoQuiz.tsx`)

Supports 3 question types:

| Type | State Variable | UI |
|------|---------------|-----|
| `multiple_choice` | `selectedAnswers[id]` | Vertical buttons |
| `true_false` | `selectedAnswers[id]` | Two horizontal buttons |
| `fill_blank` | `textAnswers[id]` | Text input + Check button |

**Navigation:** Free movement with Prev/Next + clickable dots

---

## API Client (`lib/api.ts`)

```typescript
// Session management
await api.initSession();
await api.trackWatch(postId, watchPercent, duration, event);

// Content
await api.getFeed(limit, offset, contentType?);
await api.getPost(postId);
await api.getQuiz(postId);
await api.submitQuiz(quizId, answers);

// Interactions  
await api.likePost(postId);
await api.savePost(postId);
await api.getComments(postId);
await api.createComment(postId, content);
```

**Session header required for tracking:**
```typescript
headers: { 'X-Session-Id': sessionId }
```

---

## TypeScript Interfaces

```typescript
// Post from API
interface Post {
    id: string;
    title: string;
    content_type: 'video' | 'image_slides' | 'audio' | 'quiz';
    status: 'pending' | 'processing' | 'transcribing' | 'ready' | 'failed';
    video_url?: string;
    hls_url?: string;
    dash_url?: string;
    subtitles?: { subtitles: Subtitle[] }[];  // Nested from join
    likes_count: number;
    is_liked: boolean;
    is_saved: boolean;
}

// Subtitle with word timings
interface Subtitle {
    subtitleId: string;
    text: string;
    startTime: number;  // seconds
    endTime: number;
    wordTimings: WordTiming[];
}

interface WordTiming {
    word: string;
    start: number;  // seconds
    end: number;
}

// Quiz question
interface QuizQuestion {
    id: string;
    type: 'multiple_choice' | 'fill_blank' | 'true_false';
    question: string;
    options?: QuizOption[];     // null for fill_blank/true_false
    correct_answer?: string;    // For fill_blank/true_false
    explanation?: string;
    points?: number;
}
```

---

## Common Patterns

### Video Player Cleanup Pattern

```typescript
useEffect(() => {
    let hls: Hls | null = null;
    let isMounted = true;
    
    // Setup...
    
    return () => {
        isMounted = false;
        hls?.destroy();
        video.pause();
        video.removeAttribute('src');
        video.load();  // Reset element
    };
}, [dependencies]);
```

### API Error Handling

```typescript
try {
    const data = await api.getQuiz(postId);
    setQuiz(data);
} catch (error) {
    console.error('Failed to fetch quiz:', error);
    setQuiz(null);
}
```

---

## File Structure

```
web/src/
├── pages/
│   ├── index.astro         # Main page
│   └── auth/callback.astro # OAuth callback
├── layouts/
│   └── Layout.astro        # Base HTML
├── components/
│   ├── video/
│   │   ├── VideoPlayer.tsx
│   │   ├── VideoFeed.tsx
│   │   ├── SubtitleOverlay.tsx
│   │   ├── VideoControls.tsx
│   │   ├── VideoQuiz.tsx
│   │   └── types.ts
│   └── auth/
│       ├── AuthContext.tsx
│       ├── GoogleLoginButton.tsx
│       └── UserMenu.tsx
└── lib/
    ├── api.ts              # API client + session
    └── supabase.ts         # Supabase client
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Rendered fewer hooks" | Hooks after conditional | Move ALL hooks to top |
| Video not auto-playing | Autoplay blocked | Mute video first, then play |
| Audio overlap | Previous video not paused | Add cleanup in useEffect |
| Subtitles not showing | Wrong time format | Ensure seconds, not ms |
