---
name: frontend
scope: "web/**/*"
priority: high
---

# Frontend Conventions (React + Astro)

## Hooks Order (CRITICAL)
Hooks MUST be called before any conditionals. Always put hooks at the top:
```tsx
// CORRECT
function VideoPlayer({ src }: { src: string }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const { user } = useAuth();

  if (!src) return null;  // Conditionals AFTER hooks
  ...
}

// WRONG
function VideoPlayer({ src }: { src: string }) {
  if (!src) return null;  // NO - conditionals before hooks!
  const [isPlaying, setIsPlaying] = useState(false);
  ...
}
```

## TypeScript Interfaces
Define interfaces for all component props and API responses:
```tsx
interface VideoPlayerProps {
  src: string;
  poster?: string;
  subtitles?: SubtitleTrack[];
  onProgress?: (progress: number) => void;
}

interface ApiResponse<T> {
  data: T;
  error: string | null;
}
```

## API Client
Use the Supabase client or fetch wrapper:
```tsx
import { supabase } from '@/lib/supabase';

// For authenticated requests
const { data, error } = await supabase
  .from('posts')
  .select('*')
  .eq('status', 'ready');
```

## TailwindCSS
- Use Tailwind utility classes for all styling
- Extract repeated patterns into components
- Use `dark:` prefix for dark mode support
- Use semantic colors from design system

## Video Player Cleanup
Always clean up video players to prevent memory leaks:
```tsx
useEffect(() => {
  const video = videoRef.current;
  return () => {
    if (video) {
      video.pause();
      video.src = '';
      video.load();
    }
  };
}, []);
```

## Auth Context
Always check auth state before protected operations:
```tsx
const { user, session, loading } = useAuth();
if (loading) return <LoadingSpinner />;
if (!user) return <Navigate to="/login" />;
```

## Astro Server Pages
- Use `getStaticPaths()` for static routes
- Server-render user-specific content
- Use React islands (`client:load`, `client:idle`) for interactivity
