import React, { useState, useEffect } from 'react';
import { RefreshCw, Check, X, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { api, type Quiz, type QuizQuestion } from '../../lib/api';

interface VideoQuizProps {
    postId: string;
    isOpen: boolean;
    onReplay: () => void;
    onContinue: () => void;
}

export const VideoQuiz: React.FC<VideoQuizProps> = ({ postId, isOpen, onReplay, onContinue }) => {
    const [quiz, setQuiz] = useState<Quiz | null>(null);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>({});
    const [textAnswers, setTextAnswers] = useState<Record<string, string>>({});
    const [revealedAnswers, setRevealedAnswers] = useState<Record<string, boolean>>({});
    const [isLoading, setIsLoading] = useState(false);
    const [score, setScore] = useState<number | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Fetch quiz when panel opens
    useEffect(() => {
        if (isOpen && postId) {
            fetchQuiz();
        }
    }, [isOpen, postId]);

    // Reset state when quiz closes
    useEffect(() => {
        if (!isOpen) {
            setCurrentQuestionIndex(0);
            setSelectedAnswers({});
            setTextAnswers({});
            setRevealedAnswers({});
            setScore(null);
        }
    }, [isOpen]);

    const fetchQuiz = async () => {
        setIsLoading(true);
        try {
            const data = await api.getQuiz(postId);
            setQuiz(data);
        } catch (error) {
            console.error('Failed to fetch quiz:', error);
            setQuiz(null);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    if (isLoading) {
        return (
            <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center">
                <Loader2 size={32} className="animate-spin text-white" />
                <p className="text-gray-300 mt-4">Loading quiz...</p>
            </div>
        );
    }

    if (!quiz || !quiz.questions || quiz.questions.length === 0) {
        return (
            <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center">
                <h2 className="text-2xl font-bold text-white mb-4">Great job! 🎉</h2>
                <p className="text-gray-300 mb-8">No quiz available for this video.</p>
                <div className="flex gap-4">
                    <button 
                        onClick={onReplay}
                        className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-full font-bold transition-colors"
                    >
                        <RefreshCw size={20} />
                        Replay
                    </button>
                    <button 
                        onClick={onContinue}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-bold transition-colors shadow-lg shadow-blue-500/30"
                    >
                        Next Video
                    </button>
                </div>
            </div>
        );
    }

    const currentQuestion = quiz.questions[currentQuestionIndex];
    const isFirstQuestion = currentQuestionIndex === 0;
    const isLastQuestion = currentQuestionIndex === quiz.questions.length - 1;
    const isAnswered = revealedAnswers[currentQuestion.id] || false;
    const selectedOption = selectedAnswers[currentQuestion.id];
    const textAnswer = textAnswers[currentQuestion.id] || '';

    const handleOptionClick = (optionId: string) => {
        if (isAnswered) return;
        setSelectedAnswers(prev => ({
            ...prev,
            [currentQuestion.id]: optionId
        }));
        setRevealedAnswers(prev => ({
            ...prev,
            [currentQuestion.id]: true
        }));
    };

    const handleTextSubmit = () => {
        if (!textAnswer.trim()) return;
        setRevealedAnswers(prev => ({
            ...prev,
            [currentQuestion.id]: true
        }));
    };

    const handlePrevious = () => {
        if (!isFirstQuestion) {
            setCurrentQuestionIndex(prev => prev - 1);
        }
    };

    const handleNext = () => {
        if (!isLastQuestion) {
            setCurrentQuestionIndex(prev => prev + 1);
        }
    };

    const handleFinish = async () => {
        setIsSubmitting(true);
        try {
            // Combine option answers and text answers
            const answers = quiz.questions.map(q => {
                if (q.type === 'fill_blank') {
                    return {
                        question_id: q.id,
                        text_answer: textAnswers[q.id] || ''
                    };
                }
                if (q.type === 'true_false') {
                    return {
                        question_id: q.id,
                        text_answer: selectedAnswers[q.id] || ''  // 'true' or 'false'
                    };
                }
                return {
                    question_id: q.id,
                    selected_option_id: selectedAnswers[q.id] || ''
                };
            });
            const result = await api.submitQuiz(quiz.id, answers);
            setScore(result.score);
        } catch (error) {
            console.error('Failed to submit quiz:', error);
            // Calculate local score as fallback
            let correctCount = 0;
            quiz.questions.forEach(q => {
                if (q.type === 'fill_blank' || q.type === 'true_false') {
                    const userAnswer = (q.type === 'fill_blank' 
                        ? textAnswers[q.id] 
                        : selectedAnswers[q.id] || '').toLowerCase().trim();
                    const correctAnswer = (q.correct_answer || '').toLowerCase().trim();
                    if (userAnswer === correctAnswer) correctCount++;
                } else {
                    const correctOpt = q.options?.find(o => o.is_correct);
                    if (correctOpt && selectedAnswers[q.id] === correctOpt.id) correctCount++;
                }
            });
            setScore(correctCount);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Check if fill_blank answer is correct
    const isFillBlankCorrect = () => {
        if (!currentQuestion.correct_answer) return false;
        const userAnswer = textAnswer.toLowerCase().trim();
        const correctAnswer = currentQuestion.correct_answer.toLowerCase().trim();
        return userAnswer === correctAnswer;
    };

    // Show final score
    if (score !== null) {
        const percentage = Math.round((score / quiz.questions.length) * 100);
        return (
            <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-300">
                <h2 className="text-3xl font-bold text-white mb-2">Quiz Complete! 🎉</h2>
                <div className="my-8">
                    <div className="text-6xl font-bold text-white mb-2">{percentage}%</div>
                    <p className="text-gray-300">
                        You got {score} out of {quiz.questions.length} correct
                    </p>
                </div>
                <div className="flex gap-4">
                    <button 
                        onClick={onReplay}
                        className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-full font-bold transition-colors"
                    >
                        <RefreshCw size={20} />
                        Replay
                    </button>
                    <button 
                        onClick={onContinue}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full font-bold transition-colors shadow-lg shadow-blue-500/30"
                    >
                        Next Video
                    </button>
                </div>
            </div>
        );
    }

    // Render multiple choice question
    const renderMultipleChoice = () => (
        <div className="flex flex-col gap-3 w-full max-w-xs mb-6">
            {currentQuestion.options?.map((option) => (
                <button
                    key={option.id}
                    onClick={() => handleOptionClick(option.id)}
                    disabled={isAnswered}
                    className={`p-4 rounded-xl font-semibold transition-all duration-200 transform text-left ${
                        isAnswered
                            ? option.is_correct
                                ? 'bg-green-500 text-white scale-105'
                                : selectedOption === option.id
                                    ? 'bg-red-500 text-white'
                                    : 'bg-gray-800 text-gray-500'
                            : 'bg-gray-800 text-white hover:bg-gray-700 active:scale-95'
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span>{option.text}</span>
                        {isAnswered && option.is_correct && <Check size={20} />}
                        {isAnswered && selectedOption === option.id && !option.is_correct && <X size={20} />}
                    </div>
                </button>
            ))}
        </div>
    );

    // Render true/false question
    const renderTrueFalse = () => {
        const correctAnswer = currentQuestion.correct_answer?.toLowerCase();
        const userAnswer = selectedAnswers[currentQuestion.id];
        const isCorrect = userAnswer === correctAnswer;

        return (
            <div className="flex gap-4 w-full max-w-xs mb-6 justify-center">
                {['true', 'false'].map((answer) => {
                    const isThisCorrect = answer === correctAnswer;
                    const isThisSelected = userAnswer === answer;
                    
                    return (
                        <button
                            key={answer}
                            onClick={() => {
                                if (isAnswered) return;
                                setSelectedAnswers(prev => ({
                                    ...prev,
                                    [currentQuestion.id]: answer
                                }));
                                setRevealedAnswers(prev => ({
                                    ...prev,
                                    [currentQuestion.id]: true
                                }));
                            }}
                            disabled={isAnswered}
                            className={`flex-1 p-4 rounded-xl font-semibold transition-all duration-200 transform ${
                                isAnswered
                                    ? isThisCorrect
                                        ? 'bg-green-500 text-white scale-105'
                                        : isThisSelected
                                            ? 'bg-red-500 text-white'
                                            : 'bg-gray-800 text-gray-500'
                                    : 'bg-gray-800 text-white hover:bg-gray-700 active:scale-95'
                            }`}
                        >
                            <div className="flex items-center justify-center gap-2">
                                <span className="capitalize">{answer}</span>
                                {isAnswered && isThisCorrect && <Check size={20} />}
                                {isAnswered && isThisSelected && !isThisCorrect && <X size={20} />}
                            </div>
                        </button>
                    );
                })}
            </div>
        );
    };

    // Render fill in the blank question
    const renderFillBlank = () => (
        <div className="w-full max-w-xs mb-6">
            <input
                type="text"
                value={textAnswer}
                onChange={(e) => setTextAnswers(prev => ({
                    ...prev,
                    [currentQuestion.id]: e.target.value
                }))}
                disabled={isAnswered}
                placeholder="Type your answer..."
                className={`w-full p-4 rounded-xl font-semibold transition-all duration-200 text-center ${
                    isAnswered
                        ? isFillBlankCorrect()
                            ? 'bg-green-500 text-white'
                            : 'bg-red-500 text-white'
                        : 'bg-gray-800 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 outline-none'
                }`}
                onKeyDown={(e) => {
                    if (e.key === 'Enter' && !isAnswered) {
                        handleTextSubmit();
                    }
                }}
            />
            {!isAnswered && (
                <button
                    onClick={handleTextSubmit}
                    disabled={!textAnswer.trim()}
                    className="mt-3 w-full p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-xl font-semibold transition-colors"
                >
                    Check Answer
                </button>
            )}
            {isAnswered && !isFillBlankCorrect() && (
                <p className="mt-3 text-green-400 text-sm">
                    Correct answer: <span className="font-bold">{currentQuestion.correct_answer}</span>
                </p>
            )}
            {isAnswered && currentQuestion.explanation && (
                <p className="mt-2 text-gray-400 text-sm italic">
                    {currentQuestion.explanation}
                </p>
            )}
        </div>
    );

    return (
        <div className="absolute inset-0 z-40 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-300">
            {/* Question indicator dots */}
            <div className="flex gap-2 mb-4">
                {quiz.questions.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => setCurrentQuestionIndex(idx)}
                        className={`w-2.5 h-2.5 rounded-full transition-all ${
                            idx === currentQuestionIndex
                                ? 'bg-blue-500 scale-125'
                                : revealedAnswers[quiz.questions[idx].id]
                                    ? 'bg-green-500'
                                    : 'bg-gray-600 hover:bg-gray-500'
                        }`}
                    />
                ))}
            </div>

            <div className="text-sm text-gray-400 mb-2">
                Question {currentQuestionIndex + 1} of {quiz.questions.length}
                <span className="ml-2 px-2 py-0.5 bg-gray-700 rounded text-xs">
                    {currentQuestion.type === 'fill_blank' ? 'Fill in the blank' : 
                     currentQuestion.type === 'true_false' ? 'True/False' : 'Multiple Choice'}
                </span>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Quick Quiz!</h2>
            <p className="text-gray-300 mb-6 max-w-sm">{currentQuestion.question}</p>

            {/* Render question based on type */}
            {currentQuestion.type === 'fill_blank' 
                ? renderFillBlank() 
                : currentQuestion.type === 'true_false'
                    ? renderTrueFalse()
                    : renderMultipleChoice()
            }

            {/* Show explanation after answering */}
            {isAnswered && currentQuestion.explanation && (
                <p className="text-gray-400 text-sm italic mb-4 max-w-sm">
                    💡 {currentQuestion.explanation}
                </p>
            )}

            {/* Navigation buttons - always visible */}
            <div className="flex gap-3 items-center">
                <button
                    onClick={handlePrevious}
                    disabled={isFirstQuestion}
                    className="flex items-center gap-1 px-4 py-2 bg-white/10 hover:bg-white/20 disabled:bg-white/5 disabled:text-gray-600 text-white rounded-full font-semibold transition-colors"
                >
                    <ChevronLeft size={18} />
                    Prev
                </button>

                <button 
                    onClick={onReplay}
                    className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full font-semibold transition-colors"
                >
                    <RefreshCw size={16} />
                </button>

                {isLastQuestion ? (
                    <button 
                        onClick={handleFinish}
                        disabled={isSubmitting}
                        className="flex items-center gap-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded-full font-semibold transition-colors"
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            'Finish'
                        )}
                    </button>
                ) : (
                    <button
                        onClick={handleNext}
                        className="flex items-center gap-1 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-full font-semibold transition-colors"
                    >
                        Next
                        <ChevronRight size={18} />
                    </button>
                )}
            </div>
        </div>
    );
};
