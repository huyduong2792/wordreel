import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Play, Volume2, VolumeX } from 'lucide-react';
import Hls from 'hls.js';
import { SubtitleOverlay } from './SubtitleOverlay';
import { VideoQuiz } from './VideoQuiz';
import { api } from '../../lib/api';
import type { VideoData } from './types';

interface VideoPlayerProps {
    data: VideoData;
    isActive: boolean;
    isMuted: boolean;
    onMuteChange: (muted: boolean) => void;
    onLike?: () => void;
    onSave?: () => void;
    showSubtitles: boolean;
    playbackSpeed: number;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ 
    data, 
    isActive, 
    isMuted, 
    onMuteChange, 
    onLike, 
    onSave,
    showSubtitles,
    playbackSpeed,
}) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const isMountedRef = useRef(true);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    // Track mount state for cleanup
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);
    
    // UI States
    const [isQuizOpen, setIsQuizOpen] = useState(false);
    const [isScrubbing, setIsScrubbing] = useState(false);

    // Get the real post ID (originalId for replayed videos, or id for normal)
    const postId = data.originalId || data.id;

    // Track watch progress
    const lastTrackTimeRef = useRef<number>(0);
    const trackWatch = useCallback(
        async (eventType: 'start' | 'progress' | 'pause' | 'finish' | 'seek') => {
            // For 'start' event, we don't need duration - just track it happened
            if (eventType !== 'start' && (!videoRef.current || !duration)) return;
            
            const watchPercent = duration ? Math.min(1, currentTime / duration) : 0;
            const watchDuration = currentTime;
            
            // Throttle progress events to once every 5 seconds
            if (eventType === 'progress') {
                const now = Date.now();
                if (now - lastTrackTimeRef.current < 5000) return;
                lastTrackTimeRef.current = now;
            }
            
            try {
                await api.trackWatch(postId, watchPercent, watchDuration, eventType);
            } catch (err) {
                // Silent fail for tracking
                console.debug('Track watch failed:', err);
            }
        },
        [postId, currentTime, duration]
    );

    // Sync muted state with video element
    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.muted = isMuted;
        }
    }, [isMuted]);

    // Track if we've started playing this video
    const hasStartedRef = useRef(false);
    const hasTrackedStartRef = useRef(false); // Track if we've sent 'start' event

    // Initialize Video Source (HLS or Native)
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        let hls: Hls | null = null;

        // Helper to init HLS player
        const initHls = (url: string) => {
            if (Hls.isSupported()) {
                console.log("Initializing HLS player:", url);
                hls = new Hls({
                    debug: false,
                    enableWorker: true
                });
                hls.loadSource(url);
                hls.attachMedia(video);
                
                hls.on(Hls.Events.ERROR, (event, errorData) => {
                    console.error("HLS Error:", errorData);
                    if (errorData.fatal && data.url) {
                        console.log("HLS fatal error, falling back to direct URL");
                        hls?.destroy();
                        hls = null;
                        video.src = data.url;
                    }
                });
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                // Native HLS support (Safari)
                video.src = url;
            } else if (data.url) {
                // Final fallback to direct URL
                video.src = data.url;
            }
        };

        // Priority: HLS -> Direct URL
        if (data.hlsUrl) {
            console.log("Using HLS source:", data.hlsUrl);
            initHls(data.hlsUrl);
        } else if (data.url) {
            console.log("Using direct video URL:", data.url);
            video.src = data.url;
        }
        
        return () => {
            if (hls) {
                hls.destroy();
            }
            if (video) {
                video.pause();
                video.removeAttribute('src'); 
                video.load();
            }
        };
    }, [data.url, data.hlsUrl]);

    // Auto-play/pause based on active state
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        // Cleanup function to ensure video is paused
        const pauseVideo = () => {
            try {
                video.pause();
                video.currentTime = 0;
            } catch (e) {
                // Ignore errors during cleanup
            }
        };
        
        if (isActive) {
            setIsQuizOpen(false); // Reset quiz when scrolling back
            
            // Only restart video from beginning when first becoming active
            if (!hasStartedRef.current) {
                video.currentTime = 0;
                hasStartedRef.current = true;
            }
            
            video.playbackRate = playbackSpeed;
            video.muted = isMuted; // Ensure muted state is applied before playing
            
            // Small delay to ensure DOM is ready and previous video is paused
            const playTimeout = setTimeout(() => {
                if (!videoRef.current || !isActive) return;
                
                const playPromise = videoRef.current.play();
                if (playPromise !== undefined) {
                    playPromise
                        .then(() => {
                            if (isActive) {
                                setIsPlaying(true);
                                // Track 'start' event when video first starts playing
                                if (!hasTrackedStartRef.current) {
                                    hasTrackedStartRef.current = true;
                                    trackWatch('start');
                                }
                            }
                        })
                        .catch((error) => {
                            // Auto-play was prevented
                            console.log('Autoplay prevented. Muting and retrying.', error);
                            if (videoRef.current && isActive) {
                                videoRef.current.muted = true;
                                onMuteChange(true);
                                videoRef.current.play()
                                    .then(() => {
                                        if (isActive) {
                                            setIsPlaying(true);
                                            // Track 'start' event when video first starts playing
                                            if (!hasTrackedStartRef.current) {
                                                hasTrackedStartRef.current = true;
                                                trackWatch('start');
                                            }
                                        }
                                    })
                                    .catch((e) => {
                                        console.error('Playback failed even with mute', e);
                                        setIsPlaying(false);
                                    });
                            }
                        });
                }
            }, 50);
            
            return () => {
                clearTimeout(playTimeout);
                pauseVideo();
                setIsPlaying(false);
            };
        } else {
            // Immediately pause when not active
            pauseVideo();
            setIsPlaying(false);
            hasStartedRef.current = false; // Reset so next time it becomes active, restart from beginning
            hasTrackedStartRef.current = false; // Reset so 'start' is tracked again next time
            setIsQuizOpen(false);
        }
    }, [isActive, playbackSpeed, onMuteChange]); // Removed isMuted - mute state is synced in separate useEffect

    // Update playback rate when state changes
    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.playbackRate = playbackSpeed;
        }
    }, [playbackSpeed]);

    const handleTimeUpdate = () => {
        // Don't update time from video while scrubbing to prevent jitter
        if (isScrubbing) return;
        
        if (videoRef.current) {
            setCurrentTime(videoRef.current.currentTime);
            // Also update duration if it wasn't set initially (fallback)
            if (duration === 0 && videoRef.current.duration) {
                setDuration(videoRef.current.duration);
            }
        }
    };
    
    // Handler for loaded metadata to set duration
    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            setDuration(videoRef.current.duration);
        }
    };

    const togglePlay = () => {
        if (!videoRef.current) return;
        
        if (isPlaying) {
            videoRef.current.pause();
            trackWatch('pause'); // Track pause event
        } else {
            videoRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleVideoPress = (e: React.MouseEvent) => {
        // Prevent clicking video when clicking controls
        if ((e.target as HTMLElement).closest('button')) return;
        togglePlay();
    };

    const handleVideoEnd = () => {
        setIsPlaying(false);
        setIsQuizOpen(true);
        trackWatch('finish'); // Track video finish
    };

    const handleReplay = () => {
        setIsQuizOpen(false);
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
            setIsPlaying(true);
        }
    };

    const toggleMute = (e: React.MouseEvent) => {
        e.stopPropagation();
        onMuteChange(!isMuted);
    };

    const handleProgressBarDown = (e: React.PointerEvent<HTMLDivElement>) => {
        if (!videoRef.current || !duration) return;
        e.stopPropagation(); // Prevent toggling play/pause
        setIsScrubbing(true);
        
        // Pause video while scrubbing to ensure smooth performance
        const wasPlaying = isPlaying;
        if (wasPlaying) {
            videoRef.current.pause();
        }

        const progressBar = e.currentTarget;
        const rect = progressBar.getBoundingClientRect();
        
        const updateTime = (clientX: number) => {
             const x = clientX - rect.left;
             const percentage = Math.max(0, Math.min(1, x / rect.width));
             const newTime = percentage * duration;
             
             // Update UI immediately for responsiveness
             setCurrentTime(newTime);
             
             if (videoRef.current) {
                 // Use requestAnimationFrame to decouple heavy seek from UI updates
                 requestAnimationFrame(() => {
                     if (!videoRef.current) return;
                     // Optimize seeking
                     const seekable = videoRef.current.seekable;
                     if (seekable && seekable.length > 0) {
                        // Basic bounds check
                     }

                     // @ts-ignore
                     if (typeof videoRef.current.fastSeek === 'function') {
                          // @ts-ignore
                          videoRef.current.fastSeek(newTime);
                     } else {
                          // Standard seek - can be slow on some browsers
                          videoRef.current.currentTime = newTime;
                     }
                 });
             }
        };

        // Instant update on down
        updateTime(e.clientX);
        
        const handlePointerMove = (moveEvent: PointerEvent) => {
            moveEvent.preventDefault(); // Stop scrolling/selection
            updateTime(moveEvent.clientX);
        };

        const handlePointerUp = () => {
            setIsScrubbing(false);
            trackWatch('seek'); // Track seek event
            // Resume if it was playing before
            if (wasPlaying && videoRef.current) {
                videoRef.current.play().catch(() => {});
            }
            document.removeEventListener('pointermove', handlePointerMove);
            document.removeEventListener('pointerup', handlePointerUp);
        };

        document.addEventListener('pointermove', handlePointerMove);
        document.addEventListener('pointerup', handlePointerUp);
    };

    return (
        <div className="relative w-full h-full snap-center bg-black flex justify-center items-center overflow-hidden rounded-xl">
            {/* Video Element */}
            <video
                ref={videoRef}
                className="h-full max-w-full object-contain cursor-pointer"
                playsInline
                onClick={handleVideoPress}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleVideoEnd}
            />

            {/* Quiz Overlay */}
            <VideoQuiz 
                postId={postId}
                isOpen={isQuizOpen} 
                onReplay={handleReplay}
                onContinue={() => {
                    // Logic to scroll to next would go here (might need callback to parent)
                    // For now, just close quiz
                    setIsQuizOpen(false);
                }}
            />

            {/* Play/Pause Overlay Indicator */}
            {!isPlaying && (
                <div 
                    className="absolute inset-0 flex items-center justify-center pointer-events-none bg-black/20"
                >
                    <Play size={64} className="text-white/80 fill-white/80" />
                </div>
            )}

            {/* Subtitles */}
            <SubtitleOverlay 
                currentTime={currentTime}
                subtitles={data.subtitles}
                isVisible={showSubtitles}
            />

            {/* Video Info (Left Bottom) */}
            <div className="absolute left-4 bottom-6 z-20 max-w-[85%] text-white pointer-events-none">
                <h3 className="font-bold text-shadow mb-1">{data.username}</h3>
                <p className="text-sm opacity-90 text-shadow line-clamp-2 leading-tight">
                    {data.description}
                </p>
                <div className="flex items-center gap-2 mt-2 text-xs">
                     <span className="bg-gray-800/60 px-2 py-1 rounded-md flex items-center gap-1">
                        🎵 Original Sound
                     </span>
                </div>
            </div>
            
            {/* Mute Toggle (Top Right) */}
            <button 
                onClick={toggleMute}
                className="absolute top-4 right-4 z-20 p-2 bg-black/40 rounded-full text-white/80 hover:bg-black/60 hover:text-white transition-all backdrop-blur-sm"
            >
                {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
            
            {/* Progress Bar */}
            <div 
                className={`absolute bottom-0 left-0 right-0 h-1 bg-gray-600/40 cursor-pointer group hover:h-2 transition-all z-30 touch-none rounded-b-xl ${isScrubbing ? 'h-2' : ''}`}
                onPointerDown={handleProgressBarDown}
            >
                <div 
                    className={`h-full bg-white relative ${isScrubbing ? '' : 'transition-all duration-200 ease-linear'}`}
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                >
                    <div className={`absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-md transform transition-all ${isScrubbing ? 'scale-100 opacity-100' : 'scale-0 opacity-0 group-hover:scale-100 group-hover:opacity-100'}`}/>
                </div>
            </div>
        </div>
    );
};
