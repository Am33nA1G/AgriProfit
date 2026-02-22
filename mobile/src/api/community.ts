import apiClient from './client';
import type { CommunityPost, CommunityReply } from '../types/models';
import type { PaginatedResponse } from '../types/api';

export const communityApi = {
  getPosts: (page = 1, type?: string, district?: string) =>
    apiClient.get<PaginatedResponse<CommunityPost>>('/community/posts/', {
      params: { page, limit: 20, post_type: type, district },
    }),

  getPost: (id: string) =>
    apiClient.get<CommunityPost>(`/community/posts/${id}`),

  createPost: (data: { title: string; content: string; post_type: string; district?: string }) =>
    apiClient.post<CommunityPost>('/community/posts/', data),

  deletePost: (id: string) =>
    apiClient.delete(`/community/posts/${id}`),

  getReplies: (postId: string) =>
    apiClient.get<CommunityReply[]>(`/community/posts/${postId}/replies`),

  addReply: (postId: string, content: string) =>
    apiClient.post<CommunityReply>(`/community/posts/${postId}/reply`, { content }),

  upvotePost: (postId: string) =>
    apiClient.post<void>(`/community/posts/${postId}/upvote`),

  removeUpvote: (postId: string) =>
    apiClient.delete(`/community/posts/${postId}/upvote`),

  searchPosts: (query: string) =>
    apiClient.get<CommunityPost[]>('/community/posts/search', { params: { q: query } }),
};
