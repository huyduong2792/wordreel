/**
 * Simple URL utility for share links
 */

/**
 * Generate shareable URL for a post
 */
export function getShareUrl(postId: string): string {
    const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
    return `${baseUrl}/post/${postId}`;
}

/**
 * Copy share URL to clipboard
 */
export async function copyShareUrl(postId: string): Promise<boolean> {
    try {
        const url = getShareUrl(postId);
        await navigator.clipboard.writeText(url);
        return true;
    } catch (err) {
        console.error('Failed to copy URL:', err);
        return false;
    }
}
