import React, { useState, useRef, useEffect } from 'react';
import { Heart, Bookmark, Share2, Subtitles, Gauge } from 'lucide-react';

interface VideoControlsProps {
    likes: number;
    shares: number;
    isLiked: boolean;
    isSaved: boolean;
    showSubtitles: boolean;
    playbackSpeed: number;
    onToggleLike: () => void;
    onToggleSave: () => void;
    onToggleSubtitles: () => void;
    onChangeSpeed: (speed?: number) => void;
    onShare: () => void;
}

export const VideoControls: React.FC<VideoControlsProps> = ({
    likes,
    shares,
    isLiked,
    isSaved,
    showSubtitles,
    playbackSpeed,
    onToggleLike,
    onToggleSave,
    onToggleSubtitles,
    onChangeSpeed,
    onShare
}) => {
    const [showSpeedSlider, setShowSpeedSlider] = useState(false);
    const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const isLongPress = useRef(false);

    const handleSpeedButtonDown = (e: React.PointerEvent) => {
        // Only trigger on left click/touch
        if (e.button !== 0) return;
        
        isLongPress.current = false;
        longPressTimer.current = setTimeout(() => {
            isLongPress.current = true;
            setShowSpeedSlider(true);
        }, 500); // 500ms threshold for long press
    };

    const handleSpeedButtonUp = (e: React.PointerEvent) => {
        if (longPressTimer.current) {
            clearTimeout(longPressTimer.current);
            longPressTimer.current = null;
        }

        if (!isLongPress.current) {
            // It was a click
            if (showSpeedSlider) {
                setShowSpeedSlider(false);
            } else {
                onChangeSpeed(); // Toggle behavior
            }
        }
        // If it was a long press, the slider is already open, do nothing (let user interact with slider)
    };
    
    // Close slider if clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (showSpeedSlider && !(e.target as Element).closest('.speed-control-group')) {
                setShowSpeedSlider(false);
            }
        };
        
        if (showSpeedSlider) {
            document.addEventListener('click', handleClickOutside);
        }
        
        return () => {
            document.removeEventListener('click', handleClickOutside);
        };
    }, [showSpeedSlider]);

    const speeds = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2.0];

    return (
        <div className="flex flex-col gap-6 items-center z-20 pointer-events-auto w-full">
            <button className="flex flex-col items-center gap-1" onClick={onToggleLike}>
                <div className={`p-2 rounded-full bg-gray-800/50 ${isLiked ? 'text-red-500' : 'text-white'}`}>
                    <Heart size={28} fill={isLiked ? "currentColor" : "none"} />
                </div>
                <span className="text-xs font-semibold">{likes}</span>
            </button>

            <button className="flex flex-col items-center gap-1" onClick={onToggleSave}>
                <div className={`p-2 rounded-full bg-gray-800/50 ${isSaved ? 'text-yellow-400' : 'text-white'}`}>
                    <Bookmark size={28} fill={isSaved ? "currentColor" : "none"} />
                </div>
                <span className="text-xs font-semibold">Save</span>
            </button>

            <button className="flex flex-col items-center gap-1" onClick={onToggleSubtitles}>
                <div className={`p-2 rounded-full bg-gray-800/50 ${showSubtitles ? 'text-blue-400' : 'text-white/60'}`}>
                    <Subtitles size={28} />
                </div>
                <span className="text-xs font-semibold">Subs</span>
            </button>

            <div className="relative flex flex-col items-center gap-1 speed-control-group">
                {showSpeedSlider && (
                    <div className="absolute bottom-full mb-2 right-0 bg-gray-900/90 rounded-xl p-2 flex flex-col gap-1 backdrop-blur-md border border-white/10 animate-in fade-in slide-in-from-bottom-2 duration-200 min-w-[60px]">
                        {speeds.map((speed) => (
                            <button
                                key={speed}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onChangeSpeed(speed);
                                    setShowSpeedSlider(false);
                                }}
                                className={`py-2 px-3 text-sm font-medium rounded-lg transition-colors ${
                                    playbackSpeed === speed 
                                    ? 'bg-blue-500 text-white' 
                                    : 'text-white/80 hover:bg-white/10'
                                }`}
                            >
                                {speed}x
                            </button>
                        ))}
                    </div>
                )}
                <button 
                    className="flex flex-col items-center gap-1 touch-none select-none"
                    onPointerDown={handleSpeedButtonDown}
                    onPointerUp={handleSpeedButtonUp}
                    onPointerLeave={(e) => {
                        if (longPressTimer.current && !isLongPress.current) {
                           clearTimeout(longPressTimer.current);
                           longPressTimer.current = null;
                        }
                    }}
                >
                    <div className="p-2 rounded-full bg-gray-800/50 text-white relative">
                        <Gauge size={28} />
                        <span className="absolute -top-1 -right-1 bg-blue-500 text-[10px] px-1 rounded-full">{playbackSpeed}x</span>
                    </div>
                    <span className="text-xs font-semibold">Speed</span>
                </button>
            </div>

            <button className="flex flex-col items-center gap-1" onClick={onShare}>
                <div className="p-2 rounded-full bg-gray-800/50 text-white">
                    <Share2 size={28} />
                </div>
                <span className="text-xs font-semibold">{shares}</span>
            </button>
        </div>
    );
};
