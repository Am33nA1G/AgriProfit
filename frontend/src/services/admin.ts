import api from "@/lib/api";

export const adminService = {
  async getStats() {
    const response = await api.get("/admin/stats");
    return response.data;
  },

  async getUsers(params?: { search?: string; page?: number; limit?: number }) {
    const response = await api.get("/admin/users", { params });
    return response.data;
  },

  async getPosts(params?: { search?: string; page?: number; limit?: number }) {
    const response = await api.get("/admin/posts", { params });
    return response.data;
  },

  async banUser(userId: string, reason: string) {
    const response = await api.put(`/admin/users/${userId}/ban`, { reason });
    return response.data;
  },

  async unbanUser(userId: string) {
    const response = await api.put(`/admin/users/${userId}/unban`);
    return response.data;
  },

  async deletePost(postId: string) {
    const response = await api.delete(`/admin/posts/${postId}`);
    return response.data;
  },

  async sendNotification(userId: string, title: string, message: string, type: string = "SYSTEM") {
    const response = await api.post("/notifications/", {
      user_id: userId,
      title,
      message,
      notification_type: type,
    });
    return response.data;
  },

  async sendBulkNotification(userIds: string[], title: string, message: string, type: string = "SYSTEM") {
    const response = await api.post("/notifications/bulk", {
      user_ids: userIds,
      title,
      message,
      notification_type: type,
    });
    return response.data;
  },
};
