import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, SkipBack, SkipForward } from 'lucide-react';
import { SubtitleOverlay } from './SubtitleOverlay';
import { VideoQuiz } from './VideoQuiz';
import type { VideoData } from './types';

interface AudioPlayerProps {
    data: VideoData;
    isActive: boolean;
    isMuted: boolean;
    onMuteChange: (muted: boolean) => void;
    onLike?: () => void;
    onSave?: () => void;
    showSubtitles: boolean;
    playbackSpeed: number;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ 
    data, 
    isActive, 
    isMuted, 
    onMuteChange,
    onLike,
    onSave,
    showSubtitles,
    playbackSpeed,
}) => {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    
    // UI States
    const [isQuizOpen, setIsQuizOpen] = useState(false);

    // Initialize audio source
    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const sourceUrl = data.audioUrl || data.url;
        if (sourceUrl) {
            audio.src = sourceUrl;
        }

        return () => {
            audio.pause();
        };
    }, [data.audioUrl, data.url]);

    // Sync muted state
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.muted = isMuted;
        }
    }, [isMuted]);

    // Play/pause based on active state
    useEffect(() => {
        if (isActive && audioRef.current) {
            audioRef.current.play()
                .then(() => setIsPlaying(true))
                .catch((e) => {
                    console.warn('Autoplay blocked:', e);
                    setIsPlaying(false);
                });
        } else if (audioRef.current) {
            audioRef.current.pause();
            setIsPlaying(false);
            setIsQuizOpen(false);
        }
    }, [isActive]);

    // Update playback rate
    useEffect(() => {
        if (audioRef.current) {
            audioRef.current.playbackRate = playbackSpeed;
        }
    }, [playbackSpeed]);

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime);
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const togglePlay = () => {
        if (!audioRef.current) return;
        
        if (isPlaying) {
            audioRef.current.pause();
        } else {
            audioRef.current.play();
        }
        setIsPlaying(!isPlaying);
    };

    const handleAudioEnd = () => {
        setIsPlaying(false);
        setIsQuizOpen(true);
    };

    const handleReplay = () => {
        setIsQuizOpen(false);
        if (audioRef.current) {
            audioRef.current.currentTime = 0;
            audioRef.current.play();
            setIsPlaying(true);
        }
    };

    const handleSeek = (seconds: number) => {
        if (audioRef.current) {
            audioRef.current.currentTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds));
        }
    };

    const formatTime = (time: number) => {
        const mins = Math.floor(time / 60);
        const secs = Math.floor(time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

    return (
        <div className="relative w-full h-full snap-center bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex flex-col justify-center items-center overflow-hidden">
            {/* Hidden audio element */}
            <audio
                ref={audioRef}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleAudioEnd}
            />

            {/* Quiz Overlay */}
            <VideoQuiz 
                postId={data.id}
                isOpen={isQuizOpen} 
                onReplay={handleReplay}
                onContinue={() => setIsQuizOpen(false)}
            />

            {/* Thumbnail/Waveform Visualization */}
            <div className="relative w-64 h-64 mb-8">
                {data.thumbnailUrl ? (
                    <img 
                        src={data.thumbnailUrl} 
                        alt={data.title}
                        className={`w-full h-full rounded-full object-cover shadow-2xl ${isPlaying ? 'animate-spin-slow' : ''}`}
                        style={{ animationDuration: '10s' }}
                    />
                ) : (
                    <div className={`w-full h-full rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-2xl ${isPlaying ? 'animate-pulse' : ''}`}>
                        <Volume2 size={64} className="text-white/80" />
                    </div>
                )}
                
                {/* Play/Pause button overlay */}
                <button
                    onClick={togglePlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/20 rounded-full opacity-0 hover:opacity-100 transition-opacity"
                >
                    {isPlaying ? (
                        <Pause size={64} className="text-white" />
                    ) : (
                        <Play size={64} className="text-white fill-white" />
                    )}
                </button>
            </div>

            {/* Title & Description */}
            <div className="text-center px-8 mb-6 max-w-md">
                <h2 className="text-xl font-bold text-white mb-2">{data.title}</h2>
                <p className="text-sm text-white/70">{data.username}</p>
            </div>

            {/* Progress bar */}
            <div className="w-full max-w-md px-8">
                <div className="flex items-center gap-4">
                    <span className="text-xs text-white/60 w-10">{formatTime(currentTime)}</span>
                    <div 
                        className="flex-1 h-1 bg-white/20 rounded-full cursor-pointer"
                        onClick={(e) => {
                            if (!audioRef.current) return;
                            const rect = e.currentTarget.getBoundingClientRect();
                            const percentage = (e.clientX - rect.left) / rect.width;
                            audioRef.current.currentTime = percentage * duration;
                        }}
                    >
                        <div 
                            className="h-full bg-white rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <span className="text-xs text-white/60 w-10 text-right">{formatTime(duration)}</span>
                </div>

                {/* Playback controls */}
                <div className="flex items-center justify-center gap-6 mt-4">
                    <button
                        onClick={() => handleSeek(-10)}
                        className="p-2 text-white/80 hover:text-white transition-colors"
                    >
                        <SkipBack size={24} />
                    </button>
                    <button
                        onClick={togglePlay}
                        className="p-4 bg-white rounded-full text-purple-900 hover:scale-105 transition-transform"
                    >
                        {isPlaying ? <Pause size={28} /> : <Play size={28} className="ml-1" />}
                    </button>
                    <button
                        onClick={() => handleSeek(10)}
                        className="p-2 text-white/80 hover:text-white transition-colors"
                    >
                        <SkipForward size={24} />
                    </button>
                </div>
            </div>

            {/* Subtitles */}
            <SubtitleOverlay 
                currentTime={currentTime}
                subtitles={data.subtitles}
                isVisible={showSubtitles}
            />

            {/* Mute Toggle (Top Right) */}
            <button 
                onClick={() => onMuteChange(!isMuted)}
                className="absolute top-4 right-4 z-20 p-2 bg-black/40 rounded-full text-white/80 hover:bg-black/60 hover:text-white transition-all backdrop-blur-sm"
            >
                {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
        </div>
    );
};
