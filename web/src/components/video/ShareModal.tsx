import React, { useState, useEffect } from 'react';
import { X, Copy, Check, Link2 } from 'lucide-react';

interface ShareModalProps {
    isOpen: boolean;
    onClose: () => void;
    postId: string;
}

export const ShareModal: React.FC<ShareModalProps> = ({ isOpen, onClose, postId }) => {
    const [copied, setCopied] = useState(false);
    
    // Reset copied state when modal opens
    useEffect(() => {
        if (isOpen) {
            setCopied(false);
        }
    }, [isOpen]);
    
    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };
        
        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
        }
        
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen, onClose]);
    
    if (!isOpen) return null;
    
    const shareUrl = `${window.location.origin}/post/${postId}`;
    
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            
            // Reset after 2 seconds
            setTimeout(() => {
                setCopied(false);
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = shareUrl;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };
    
    return (
        <div 
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={onClose}
        >
            <div 
                className="bg-[#1f1f1f] rounded-2xl w-full max-w-md mx-4 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-white/10">
                    <h2 className="text-lg font-semibold text-white">Share</h2>
                    <button 
                        onClick={onClose}
                        className="p-1 rounded-full hover:bg-white/10 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>
                
                {/* Content */}
                <div className="p-4 space-y-4">
                    {/* Copy Link Section */}
                    <div className="space-y-2">
                        <label className="text-sm text-gray-400 flex items-center gap-2">
                            <Link2 size={16} />
                            Copy link
                        </label>
                        <div className="flex gap-2">
                            <input 
                                type="text"
                                value={shareUrl}
                                readOnly
                                className="flex-1 bg-[#2f2f2f] text-white text-sm px-4 py-3 rounded-lg border border-white/10 focus:outline-none focus:border-blue-500"
                                onClick={(e) => (e.target as HTMLInputElement).select()}
                            />
                            <button
                                onClick={handleCopy}
                                className={`px-4 py-3 rounded-lg font-medium transition-all flex items-center gap-2 ${
                                    copied 
                                        ? 'bg-green-500 text-white' 
                                        : 'bg-[#fe2c55] hover:bg-[#ef2950] text-white'
                                }`}
                            >
                                {copied ? (
                                    <>
                                        <Check size={18} />
                                        Copied!
                                    </>
                                ) : (
                                    <>
                                        <Copy size={18} />
                                        Copy
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
