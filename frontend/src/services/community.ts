import api from '@/lib/api';

// Post types mapping (backend uses these values)
export type PostType = 'discussion' | 'question' | 'tip' | 'announcement' | 'alert';

// Display labels for post types
export const POST_TYPE_LABELS: Record<PostType, string> = {
    discussion: 'General',
    question: 'Question',
    tip: 'Tip',
    announcement: 'Announcement',
    alert: 'Alert',
};

export const POST_TYPE_COLORS: Record<PostType, string> = {
    discussion: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    question: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
    tip: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
    announcement: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
    alert: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
};

export interface CommunityPost {
    id: string;
    title: string;
    content: string;
    user_id: string;
    post_type: PostType;
    district: string | null;
    is_admin_override: boolean;
    image_url: string | null;
    view_count: number;
    is_pinned: boolean;
    created_at: string;
    updated_at: string;
    likes_count: number;
    replies_count: number;
    user_has_liked: boolean;
    alert_highlight: boolean;
    // Extended fields (may be populated by joins)
    author_name?: string;
    author_state?: string;
    author_district?: string;
}

export interface AlertStatusResponse {
    is_alert: boolean;
    should_highlight: boolean;
    in_affected_area: boolean;
    author_district: string | null;
}

export interface CommunityPostListResponse {
    items: CommunityPost[];
    total: number;
    skip: number;
    limit: number;
}

export interface CommunityReply {
    id: string;
    post_id: string;
    user_id: string;
    content: string;
    created_at: string;
    author_name?: string;
}

export interface CreatePostData {
    title: string;
    content: string;
    post_type: PostType;
    district?: string;
    image_url?: string;
}

export interface UpdatePostData {
    title?: string;
    content?: string;
    post_type?: PostType;
    district?: string;
}

export const communityService = {
    /**
     * Get all posts with optional filters
     */
    async getPosts(params?: {
        skip?: number;
        limit?: number;
        user_id?: string;
        post_type?: PostType;
        district?: string;
    }): Promise<CommunityPostListResponse> {
        const response = await api.get('/community/posts/', { params });
        return response.data;
    },

    /**
     * Search posts by query
     */
    async searchPosts(query: string, limit: number = 20): Promise<CommunityPost[]> {
        const response = await api.get('/community/posts/search', {
            params: { q: query, limit }
        });
        return response.data;
    },

    /**
     * Get a single post by ID
     */
    async getPost(postId: string): Promise<CommunityPost> {
        const response = await api.get(`/community/posts/${postId}`);
        return response.data;
    },

    /**
     * Create a new post
     */
    async createPost(data: CreatePostData): Promise<CommunityPost> {
        const response = await api.post('/community/posts/', data);
        return response.data;
    },

    /**
     * Update an existing post
     */
    async updatePost(postId: string, data: UpdatePostData): Promise<CommunityPost> {
        const response = await api.put(`/community/posts/${postId}`, data);
        return response.data;
    },

    /**
     * Delete a post
     */
    async deletePost(postId: string): Promise<void> {
        await api.delete(`/community/posts/${postId}`);
    },

    /**
     * Get replies for a post
     */
    async getReplies(postId: string): Promise<CommunityReply[]> {
        // Note: The backend may need to implement this endpoint
        // For now, replies might come with the post detail
        const response = await api.get(`/community/posts/${postId}/replies`);
        return response.data;
    },

    /**
     * Add a reply to a post
     */
    async addReply(postId: string, content: string): Promise<CommunityReply> {
        const response = await api.post(`/community/posts/${postId}/reply`, { content });
        return response.data;
    },

    /**
     * Upvote a post
     */
    async upvotePost(postId: string): Promise<void> {
        await api.post(`/community/posts/${postId}/upvote`);
    },

    /**
     * Remove upvote from a post
     */
    async removeUpvote(postId: string): Promise<void> {
        await api.delete(`/community/posts/${postId}/upvote`);
    },

    /**
     * Get posts by type
     */
    async getPostsByType(postType: PostType, limit: number = 100): Promise<CommunityPost[]> {
        const response = await api.get(`/community/posts/type/${postType}`, {
            params: { limit }
        });
        return response.data;
    },

    /**
     * Get posts by district
     */
    async getPostsByDistrict(district: string, limit: number = 100): Promise<CommunityPost[]> {
        const response = await api.get(`/community/posts/district/${district}`, {
            params: { limit }
        });
        return response.data;
    },

    /**
     * Get alert status for a post (whether it affects the current user's area)
     */
    async getAlertStatus(postId: string): Promise<AlertStatusResponse> {
        const response = await api.get(`/community/posts/${postId}/alert-status`);
        return response.data;
    },
};

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) {
        return 'just now';
    }

    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) {
        return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
    }

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) {
        return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    }

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) {
        return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
    }

    const diffInWeeks = Math.floor(diffInDays / 7);
    if (diffInWeeks < 4) {
        return `${diffInWeeks} week${diffInWeeks > 1 ? 's' : ''} ago`;
    }

    const diffInMonths = Math.floor(diffInDays / 30);
    if (diffInMonths < 12) {
        return `${diffInMonths} month${diffInMonths > 1 ? 's' : ''} ago`;
    }

    const diffInYears = Math.floor(diffInDays / 365);
    return `${diffInYears} year${diffInYears > 1 ? 's' : ''} ago`;
}
