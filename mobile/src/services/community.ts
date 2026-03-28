// mobile/src/services/community.ts
// Community posts API service — mirrors frontend/src/services/community.ts

import api from '../lib/api';

export type PostType = 'discussion' | 'question' | 'tip' | 'announcement' | 'alert';

export const POST_TYPE_LABELS: Record<PostType, string> = {
    discussion: 'General',
    question: 'Question',
    tip: 'Tip',
    announcement: 'Announcement',
    alert: 'Alert',
};

// Hex colours for badge backgrounds
export const POST_TYPE_COLORS: Record<PostType, string> = {
    discussion: '#3b82f6',
    question: '#22c55e',
    tip: '#a855f7',
    announcement: '#f97316',
    alert: '#ef4444',
};

export interface CommunityPost {
    id: string;
    title: string;
    content: string;
    user_id: string;
    post_type: PostType;
    district: string | null;
    image_url: string | null;
    likes_count: number;
    replies_count: number;
    user_has_liked: boolean;
    created_at: string;
    updated_at: string;
    author_name?: string;
}

export interface CommunityReply {
    id: string;
    post_id: string;
    user_id: string;
    content: string;
    created_at: string;
    author_name?: string;
}

export const communityService = {
    // Backend returns paginated envelope { items, total, skip, limit } — extract .items
    async listPosts(params?: { post_type?: PostType; limit?: number }): Promise<CommunityPost[]> {
        const { data } = await api.get('/community/posts', { params });
        return data.items;
    },

    async createPost(payload: { title: string; content: string; post_type: PostType; image_url?: string | null }): Promise<CommunityPost> {
        const { data } = await api.post('/community/posts', payload);
        return data;
    },

    async uploadImage(localUri: string): Promise<string> {
        const filename = localUri.split('/').pop() ?? 'photo.jpg';
        const ext = filename.split('.').pop()?.toLowerCase() ?? 'jpg';
        const mimeMap: Record<string, string> = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif', webp: 'image/webp' };
        const form = new FormData();
        form.append('file', { uri: localUri, name: filename, type: mimeMap[ext] ?? 'image/jpeg' } as unknown as Blob);
        const { data } = await api.post('/uploads/image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
        return data.url as string;
    },

    async updatePost(id: string, payload: { title?: string; content?: string; post_type?: PostType }): Promise<CommunityPost> {
        const { data } = await api.put(`/community/posts/${id}`, payload);
        return data;
    },

    async deletePost(id: string): Promise<void> {
        await api.delete(`/community/posts/${id}`);
    },

    async addUpvote(post_id: string): Promise<void> {
        await api.post(`/community/posts/${post_id}/upvote`);
    },

    async removeUpvote(post_id: string): Promise<void> {
        await api.delete(`/community/posts/${post_id}/upvote`);
    },

    async getReplies(post_id: string): Promise<CommunityReply[]> {
        const { data } = await api.get(`/community/posts/${post_id}/replies`);
        return data;
    },

    // Note: endpoint is /reply (singular), not /replies
    async addReply(post_id: string, content: string): Promise<CommunityReply> {
        const { data } = await api.post(`/community/posts/${post_id}/reply`, { content });
        return data;
    },
};

export function formatRelativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}
