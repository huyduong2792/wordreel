import React, { useState, useEffect } from 'react';
import { AuthProvider } from '../auth';
import { VideoFeed } from '../video/VideoFeed';
import { CommentsPanel } from '../video/CommentsPanel';
import { AppShell } from '../shell';
import { api } from '../../lib/api';

interface AppContentProps {
    initialPostId?: string;
    sessionReady: boolean;
}

const AppContent: React.FC<AppContentProps> = ({ initialPostId, sessionReady }) => {
    const [activePostId, setActivePostId] = useState<string>('');
    const [activeCommentsCount, setActiveCommentsCount] = useState<number>(0);

    return (
        <AppShell
            activeNavItem="home"
            showRightPanel
            renderRightPanel={() =>
                activePostId ? (
                    <CommentsPanel
                        postId={activePostId}
                        commentsCount={activeCommentsCount}
                    />
                ) : (
                    <div className="h-full flex items-center justify-center text-gray-500">
                        <p>Select a video to see comments</p>
                    </div>
                )
            }
        >
            <VideoFeed
                onActivePostChange={(postId, commentsCount) => {
                    setActivePostId(postId);
                    setActiveCommentsCount(commentsCount);
                }}
                initialPostId={initialPostId}
                sessionReady={sessionReady}
            />
        </AppShell>
    );
};

interface AppProps {
    initialPostId?: string;
}

export const App: React.FC<AppProps> = ({ initialPostId }) => {
    const [sessionReady, setSessionReady] = useState(false);

    useEffect(() => {
        api.initSession()
            .then(() => setSessionReady(true))
            .catch(() => setSessionReady(true));
    }, []);

    return (
        <AuthProvider>
            <AppContent initialPostId={initialPostId} sessionReady={sessionReady} />
        </AuthProvider>
    );
};
