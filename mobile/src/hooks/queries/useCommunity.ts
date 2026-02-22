import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { communityApi } from '../../api/community';
import { useNetworkStore } from '../../store/networkStore';
import { enqueueOperation } from '../../services/offlineQueue';

const POSTS_KEY = ['community', 'posts'];

export function usePosts(page = 1, type?: string, district?: string) {
  return useQuery({
    queryKey: [...POSTS_KEY, page, type, district],
    queryFn: () => communityApi.getPosts(page, type, district),
    staleTime: 2 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function usePost(id: string) {
  return useQuery({
    queryKey: [...POSTS_KEY, id],
    queryFn: () => communityApi.getPost(id),
    staleTime: 2 * 60 * 1000,
    enabled: !!id,
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (data: Parameters<typeof communityApi.createPost>[0]) => {
      if (!isConnected) {
        enqueueOperation('post_create', 'POST', '/community/posts/', data);
        throw new Error('OFFLINE_QUEUED');
      }
      return communityApi.createPost(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: POSTS_KEY }),
    onError: (err: Error) => {
      if (err.message === 'OFFLINE_QUEUED') return;
    },
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: communityApi.deletePost,
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: POSTS_KEY });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: POSTS_KEY }),
  });
}

export function useReplies(postId: string) {
  return useQuery({
    queryKey: ['community', 'replies', postId],
    queryFn: () => communityApi.getReplies(postId),
    staleTime: 60 * 1000,
    enabled: !!postId,
  });
}

export function useAddReply(postId: string) {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async (content: string) => {
      if (!isConnected) {
        enqueueOperation('reply_add', 'POST', `/community/posts/${postId}/reply`, { content });
        throw new Error('OFFLINE_QUEUED');
      }
      return communityApi.addReply(postId, content);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['community', 'replies', postId] }),
    onError: (err: Error) => {
      if (err.message === 'OFFLINE_QUEUED') return;
    },
  });
}

export function useUpvotePost(postId: string) {
  const qc = useQueryClient();
  const isConnected = useNetworkStore(s => s.isConnected);

  return useMutation({
    mutationFn: async ({ action }: { action: 'upvote' | 'remove' }) => {
      if (!isConnected) {
        const endpoint = `/community/posts/${postId}/upvote`;
        enqueueOperation(
          `post_${action}`,
          action === 'upvote' ? 'POST' : 'DELETE',
          endpoint,
        );
        return;
      }
      return action === 'upvote'
        ? communityApi.upvotePost(postId)
        : communityApi.removeUpvote(postId);
    },
    onMutate: async ({ action }) => {
      await qc.cancelQueries({ queryKey: [...POSTS_KEY, postId] });
      const prev = qc.getQueryData([...POSTS_KEY, postId]);
      qc.setQueryData([...POSTS_KEY, postId], (old: any) => {
        if (!old?.data) return old;
        return {
          ...old,
          data: {
            ...old.data,
            upvote_count: old.data.upvote_count + (action === 'upvote' ? 1 : -1),
            user_has_upvoted: action === 'upvote',
          },
        };
      });
      return { prev };
    },
    onError: (_err: any, _vars: any, context: any) => {
      if (context?.prev) qc.setQueryData([...POSTS_KEY, postId], context.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: [...POSTS_KEY, postId] }),
  });
}
