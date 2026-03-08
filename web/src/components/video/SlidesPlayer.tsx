import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Volume2, VolumeX } from 'lucide-react';
import { VideoQuiz } from './VideoQuiz';
import type { VideoData } from './types';

interface SlidesPlayerProps {
    data: VideoData;
    isActive: boolean;
    isMuted: boolean;
    onMuteChange: (muted: boolean) => void;
    onLike?: () => void;
    onSave?: () => void;
    showSubtitles: boolean;
    playbackSpeed: number;
}

export const SlidesPlayer: React.FC<SlidesPlayerProps> = ({ 
    data, 
    isActive, 
    isMuted, 
    onMuteChange,
    onLike,
    onSave,
    showSubtitles,
    playbackSpeed,
}) => {
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const [isAutoPlaying, setIsAutoPlaying] = useState(false);
    const autoPlayRef = useRef<NodeJS.Timeout | null>(null);
    
    // UI States
    const [isQuizOpen, setIsQuizOpen] = useState(false);

    const slides = data.slides || [];
    const totalSlides = slides.length;

    // Auto-play slides when active
    useEffect(() => {
        if (isActive && totalSlides > 1) {
            setIsAutoPlaying(true);
        } else {
            setIsAutoPlaying(false);
        }
    }, [isActive, totalSlides]);

    // Auto-advance slides
    useEffect(() => {
        if (isAutoPlaying && totalSlides > 1) {
            autoPlayRef.current = setInterval(() => {
                setCurrentSlideIndex(prev => {
                    const next = prev + 1;
                    if (next >= totalSlides) {
                        setIsAutoPlaying(false);
                        setIsQuizOpen(true);
                        return prev;
                    }
                    return next;
                });
            }, 5000); // 5 seconds per slide
        }

        return () => {
            if (autoPlayRef.current) {
                clearInterval(autoPlayRef.current);
            }
        };
    }, [isAutoPlaying, totalSlides]);

    const goToSlide = useCallback((index: number) => {
        if (index >= 0 && index < totalSlides) {
            setCurrentSlideIndex(index);
            setIsAutoPlaying(false);
        }
    }, [totalSlides]);

    const nextSlide = useCallback(() => {
        if (currentSlideIndex < totalSlides - 1) {
            goToSlide(currentSlideIndex + 1);
        }
    }, [currentSlideIndex, totalSlides, goToSlide]);

    const prevSlide = useCallback(() => {
        if (currentSlideIndex > 0) {
            goToSlide(currentSlideIndex - 1);
        }
    }, [currentSlideIndex, goToSlide]);

    const handleReplay = () => {
        setIsQuizOpen(false);
        setCurrentSlideIndex(0);
        setIsAutoPlaying(true);
    };

    // Touch/swipe handling
    const touchStartX = useRef<number>(0);
    const handleTouchStart = (e: React.TouchEvent) => {
        touchStartX.current = e.touches[0].clientX;
    };
    const handleTouchEnd = (e: React.TouchEvent) => {
        const diff = touchStartX.current - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) {
            if (diff > 0) nextSlide();
            else prevSlide();
        }
    };

    if (totalSlides === 0) {
        return (
            <div className="relative w-full h-full snap-center bg-gray-900 flex items-center justify-center">
                <p className="text-gray-400">No slides available</p>
            </div>
        );
    }

    const currentSlide = slides[currentSlideIndex];

    return (
        <div 
            className="relative w-full h-full snap-center bg-black flex flex-col justify-center items-center overflow-hidden"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
        >
            {/* Quiz Overlay */}
            <VideoQuiz 
                postId={data.id}
                isOpen={isQuizOpen} 
                onReplay={handleReplay}
                onContinue={() => setIsQuizOpen(false)}
            />

            {/* Slide Image */}
            <div className="relative w-full h-full flex items-center justify-center">
                <img 
                    src={currentSlide.url} 
                    alt={currentSlide.caption || `Slide ${currentSlideIndex + 1}`}
                    className="max-w-full max-h-full object-contain"
                />

                {/* Navigation arrows */}
                {currentSlideIndex > 0 && (
                    <button
                        onClick={prevSlide}
                        className="absolute left-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
                    >
                        <ChevronLeft size={24} />
                    </button>
                )}
                {currentSlideIndex < totalSlides - 1 && (
                    <button
                        onClick={nextSlide}
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors"
                    >
                        <ChevronRight size={24} />
                    </button>
                )}
            </div>

            {/* Caption */}
            {currentSlide.caption && (
                <div className="absolute bottom-32 left-0 right-0 px-8 text-center">
                    <div className="inline-block bg-black/60 backdrop-blur-sm px-4 py-2 rounded-xl">
                        <p className="text-lg text-white">{currentSlide.caption}</p>
                    </div>
                </div>
            )}

            {/* Slide indicators */}
            <div className="absolute bottom-20 left-0 right-0 flex justify-center gap-2 px-4">
                {slides.map((_, index) => (
                    <button
                        key={index}
                        onClick={() => goToSlide(index)}
                        className={`w-2 h-2 rounded-full transition-all ${
                            index === currentSlideIndex 
                                ? 'bg-white w-6' 
                                : 'bg-white/40 hover:bg-white/60'
                        }`}
                    />
                ))}
            </div>

            {/* Progress bar */}
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-600/40">
                <div 
                    className="h-full bg-white transition-all duration-500"
                    style={{ width: `${((currentSlideIndex + 1) / totalSlides) * 100}%` }}
                />
            </div>

            {/* Video Info (Left Bottom) */}
            <div className="absolute left-4 bottom-6 z-20 max-w-[85%] text-white pointer-events-none">
                <h3 className="font-bold text-shadow mb-1">{data.username}</h3>
                <p className="text-sm opacity-90 text-shadow line-clamp-2 leading-tight">
                    {data.title}
                </p>
                <p className="text-xs text-white/70 mt-1">
                    {currentSlideIndex + 1} / {totalSlides}
                </p>
            </div>
        </div>
    );
};
