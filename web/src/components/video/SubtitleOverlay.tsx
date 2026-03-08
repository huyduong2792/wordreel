import React, { useMemo } from 'react';
import type { SubtitleDisplay } from './types';

interface SubtitleOverlayProps {
    currentTime: number;
    subtitles: SubtitleDisplay[];
    isVisible: boolean;
}

// Maximum words per line for readability
const MAX_WORDS_PER_LINE = 6;

export const SubtitleOverlay: React.FC<SubtitleOverlayProps> = ({
    currentTime,
    subtitles,
    isVisible
}) => {
    // ALL hooks must be called before any conditional returns (React Rules of Hooks)
    const currentSubtitle = useMemo(() => {
        return subtitles.find(sub => currentTime >= sub.startTime && currentTime <= sub.endTime);
    }, [currentTime, subtitles]);

    // Split words into lines for better readability
    const wordLines = useMemo(() => {
        if (!currentSubtitle?.wordTimings) return [];
        
        const lines: typeof currentSubtitle.wordTimings[] = [];
        for (let i = 0; i < currentSubtitle.wordTimings.length; i += MAX_WORDS_PER_LINE) {
            lines.push(currentSubtitle.wordTimings.slice(i, i + MAX_WORDS_PER_LINE));
        }
        return lines;
    }, [currentSubtitle?.wordTimings]);

    // Conditional returns AFTER all hooks
    if (!isVisible || !currentSubtitle) return null;

    return (
        <div className="absolute bottom-32 left-4 right-20 flex justify-center pointer-events-none z-10">
            <div className="max-w-full bg-black/70 backdrop-blur-sm px-5 py-3 rounded-2xl">
                {currentSubtitle.wordTimings ? (
                    <div className="flex flex-col items-center gap-1">
                        {wordLines.map((line, lineIdx) => (
                            <p key={lineIdx} className="text-lg md:text-xl font-bold leading-relaxed text-center">
                                {line.map((wordInfo, idx) => {
                                    const isHighlighted = currentTime >= wordInfo.start && currentTime <= wordInfo.end;
                                    const isPast = currentTime > wordInfo.end;
                                    
                                    return (
                                        <span
                                            key={`${currentSubtitle.id}-${lineIdx}-${idx}`}
                                            className={`inline-block mx-0.5 transition-all duration-150 ${
                                                isHighlighted 
                                                    ? 'text-yellow-400 font-extrabold' 
                                                    : isPast 
                                                        ? 'text-white/90' 
                                                        : 'text-white/60'
                                            }`}
                                            style={{
                                                // Use text-shadow for emphasis instead of scale (prevents reflow)
                                                textShadow: isHighlighted 
                                                    ? '0 0 20px rgba(250, 204, 21, 0.8), 0 0 40px rgba(250, 204, 21, 0.4)' 
                                                    : 'none'
                                            }}
                                        >
                                            {wordInfo.word}
                                        </span>
                                    );
                                })}
                            </p>
                        ))}
                    </div>
                ) : (
                    <p className="text-lg md:text-xl font-bold leading-relaxed text-center text-white">
                        {currentSubtitle.text}
                    </p>
                )}
            </div>
        </div>
    );
};