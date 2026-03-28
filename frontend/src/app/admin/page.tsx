"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  Users,
  MessageSquare,
  Shield,
  AlertTriangle,
  Search,
  MoreVertical,
  Ban,
  CheckCircle,
  Trash2,
  Bell
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { AppLayout } from "@/components/layout/AppLayout";
import { adminService } from "@/services/admin";

export default function AdminPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Get user from localStorage
  const [user, setUser] = useState<any>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // Check auth on mount
  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      const parsed = JSON.parse(userData);
      
      // Route protection
      if (!parsed || parsed.role !== "admin") {
        router.push("/dashboard");
        toast.error("Access denied. Admin only.");
        return;
      }
      
      setUser(parsed);
    } else {
      router.push("/login");
      return;
    }
    
    setIsCheckingAuth(false);
  }, [router]); // Include router in dependencies

  // State
  const [searchUsers, setSearchUsers] = useState("");
  const [searchPosts, setSearchPosts] = useState("");
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [banDialogOpen, setBanDialogOpen] = useState(false);
  const [banReason, setBanReason] = useState("");
  const [unbanDialogOpen, setUnbanDialogOpen] = useState(false);
  const [deletePostDialog, setDeletePostDialog] = useState<any>(null);
  const [notificationDialogOpen, setNotificationDialogOpen] = useState(false);
  const [notificationTitle, setNotificationTitle] = useState("");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [broadcastDialogOpen, setBroadcastDialogOpen] = useState(false);
  const [broadcastTitle, setBroadcastTitle] = useState("");
  const [broadcastMessage, setBroadcastMessage] = useState("");
  const [broadcastToAll, setBroadcastToAll] = useState(true);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState("users");

  // Fetch stats
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminService.getStats(),
    enabled: !!user && user.role === "admin",
    retry: 2,
    retryDelay: 1000,
    staleTime: 2 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  // Fetch users
  const { data: usersData, isLoading: usersLoading, error: usersError } = useQuery({
    queryKey: ["admin-users", searchUsers],
    queryFn: () => {
      return adminService.getUsers({ search: searchUsers });
    },
    enabled: !!user && user.role === "admin",
    retry: 2,
    retryDelay: 1000,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  // Fetch posts
  const { data: postsData, isLoading: postsLoading, error: postsError } = useQuery({
    queryKey: ["admin-posts", searchPosts],
    queryFn: () => {
      return adminService.getPosts({ search: searchPosts });
    },
    enabled: !!user && user.role === "admin",
    retry: 2,
    retryDelay: 1000,
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });

  // Debug logging removed - was causing memory issues during tests

  // Ban user mutation
  const banUserMutation = useMutation({
    mutationFn: ({ userId, reason }: { userId: string; reason: string }) =>
      adminService.banUser(userId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
      toast.success("User banned successfully");
      setBanDialogOpen(false);
      setBanReason("");
      setSelectedUser(null);
    },
    onError: () => {
      toast.error("Failed to ban user");
    },
  });

  // Unban user mutation
  const unbanUserMutation = useMutation({
    mutationFn: (userId: string) => adminService.unbanUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
      toast.success("User unbanned successfully");
      setUnbanDialogOpen(false);
      setSelectedUser(null);
    },
    onError: () => {
      toast.error("Failed to unban user");
    },
  });

  // Delete post mutation
  const deletePostMutation = useMutation({
    mutationFn: (postId: string) => adminService.deletePost(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-posts"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
      toast.success("Post deleted successfully");
      setDeletePostDialog(null);
    },
    onError: () => {
      toast.error("Failed to delete post");
    },
  });

  // Send notification mutation
  const sendNotificationMutation = useMutation({
    mutationFn: ({ userId, title, message }: { userId: string; title: string; message: string }) =>
      adminService.sendNotification(userId, title, message),
    onSuccess: () => {
      toast.success("Notification sent successfully");
      setNotificationDialogOpen(false);
      setNotificationTitle("");
      setNotificationMessage("");
      setSelectedUser(null);
    },
    onError: () => {
      toast.error("Failed to send notification");
    },
  });

  // Broadcast notification mutation
  const broadcastNotificationMutation = useMutation({
    mutationFn: ({ userIds, title, message }: { userIds: string[]; title: string; message: string }) =>
      adminService.sendBulkNotification(userIds, title, message),
    onSuccess: (data) => {
      toast.success(`Notification sent to ${data.length} user(s)`);
      setBroadcastDialogOpen(false);
      setBroadcastTitle("");
      setBroadcastMessage("");
      setSelectedUserIds([]);
      setBroadcastToAll(true);
    },
    onError: () => {
      toast.error("Failed to broadcast notification");
    },
  });

  const handleBanClick = (user: any) => {
    setSelectedUser(user);
    setBanDialogOpen(true);
  };

  const handleUnbanClick = (user: any) => {
    setSelectedUser(user);
    setUnbanDialogOpen(true);
  };

  const handleNotificationClick = (user: any) => {
    setSelectedUser(user);
    setNotificationDialogOpen(true);
  };

  const handleBanConfirm = () => {
    if (!selectedUser || !banReason.trim()) {
      toast.error("Please provide a reason for banning");
      return;
    }
    banUserMutation.mutate({
      userId: selectedUser.id,
      reason: banReason,
    });
  };

  const handleUnbanConfirm = () => {
    if (!selectedUser) return;
    unbanUserMutation.mutate(selectedUser.id);
  };

  const handleDeletePost = (postId: string) => {
    deletePostMutation.mutate(postId);
  };

  const handleSendNotification = () => {
    if (!selectedUser || !notificationTitle.trim() || !notificationMessage.trim()) {
      toast.error("Please provide both title and message");
      return;
    }
    sendNotificationMutation.mutate({
      userId: selectedUser.id,
      title: notificationTitle,
      message: notificationMessage,
    });
  };

  const handleBroadcastSend = () => {
    if (!broadcastTitle.trim() || !broadcastMessage.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    let userIds: string[];
    if (broadcastToAll) {
      userIds = usersData?.map((user: any) => user.id) || [];
    } else {
      userIds = selectedUserIds;
    }

    if (userIds.length === 0) {
      toast.error("Please select at least one user");
      return;
    }

    broadcastNotificationMutation.mutate({
      userIds,
      title: broadcastTitle,
      message: broadcastMessage,
    });
  };

  const toggleUserSelection = (userId: string) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    );
  };

  const toggleAllUsers = () => {
    if (selectedUserIds.length === usersData?.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(usersData?.map((user: any) => user.id) || []);
    }
  };

  // Show loading while checking auth
  if (isCheckingAuth) {
    return null;
  }

  // Don't render if not admin
  if (!user || user.role !== "admin") {
    return null;
  }

  return (
    <AppLayout>
      <div className="container mx-auto p-6 space-y-6">
        {/* Backend Connection Error */}
        {(statsError || usersError || postsError) && (
          <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            <div>
              <p className="font-semibold">Backend Connection Error</p>
              <p className="text-sm">
                Cannot connect to the API server. Please ensure the backend is running on{" "}
                <code className="bg-destructive/20 px-1 rounded">http://127.0.0.1:8000</code>
              </p>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
            <p className="text-muted-foreground">
              Manage users, moderate content, and monitor system
            </p>
          </div>
          <Badge variant="destructive" className="gap-1">
            <Shield className="h-3 w-3" />
            Admin Access
          </Badge>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statsLoading ? "..." : stats?.total_users || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Registered farmers
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Posts</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statsLoading ? "..." : stats?.total_posts || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Community discussions
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Users</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statsLoading ? "..." : (stats?.total_users || 0) - (stats?.banned_users || 0)}
              </div>
              <p className="text-xs text-muted-foreground">
                Currently active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Banned Users</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {statsLoading ? "..." : stats?.banned_users || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                Currently banned
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for User Management and Post Moderation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList>
            <TabsTrigger value="users">User Management</TabsTrigger>
            <TabsTrigger value="posts">Post Moderation</TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users">
            <Card>
              <CardHeader>
                <CardTitle>User Management</CardTitle>
                <CardDescription>
                  View and manage all registered users - Total: {usersData?.length || 0}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 flex-1">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search users by name, phone, or location..."
                    value={searchUsers}
                    onChange={(e) => setSearchUsers(e.target.value)}
                    className="max-w-md"
                  />
                </div>
                <Button
                  onClick={() => setBroadcastDialogOpen(true)}
                  className="flex items-center gap-2"
                >
                  <Bell className="h-4 w-4" />
                  Broadcast Notification
                </Button>
              </div>

                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Phone</TableHead>
                        <TableHead>Location</TableHead>
                        <TableHead>Joined</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {usersLoading ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            Loading users...
                          </TableCell>
                        </TableRow>
                      ) : usersError ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-red-600">
                            Error loading users: {usersError.message}
                          </TableCell>
                        </TableRow>
                      ) : !usersData || usersData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            No users found
                          </TableCell>
                        </TableRow>
                      ) : (
                        usersData.map((user: any) => (
                          <TableRow key={user.id}>
                            <TableCell className="font-medium">
                              {user.name}
                            </TableCell>
                            <TableCell>{user.phone}</TableCell>
                            <TableCell>
                              {user.location}
                            </TableCell>
                            <TableCell>
                              {new Date(user.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              {user.is_banned ? (
                                <Badge variant="destructive">Banned</Badge>
                              ) : (
                                <Badge variant="default" className="bg-green-600">
                                  Active
                                </Badge>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="sm">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuItem
                                    onClick={() => handleNotificationClick(user)}
                                  >
                                    <Bell className="mr-2 h-4 w-4" />
                                    Send Notification
                                  </DropdownMenuItem>
                                  {user.is_banned ? (
                                    <DropdownMenuItem
                                      onClick={() => handleUnbanClick(user)}
                                    >
                                      <CheckCircle className="mr-2 h-4 w-4" />
                                      Unban User
                                    </DropdownMenuItem>
                                  ) : (
                                    <DropdownMenuItem
                                      onClick={() => handleBanClick(user)}
                                      className="text-red-600"
                                    >
                                      <Ban className="mr-2 h-4 w-4" />
                                      Ban User
                                    </DropdownMenuItem>
                                  )}
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Posts Tab */}
          <TabsContent value="posts">
            <Card>
              <CardHeader>
                <CardTitle>Post Moderation</CardTitle>
                <CardDescription>
                  Review and moderate community posts
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search posts by title or author..."
                      value={searchPosts}
                      onChange={(e) => setSearchPosts(e.target.value)}
                      className="max-w-md"
                    />
                  </div>
                </div>

                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Author</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Posted</TableHead>
                        <TableHead>Engagement</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {postsLoading ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            Loading posts...
                          </TableCell>
                        </TableRow>
                      ) : postsError ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8 text-red-600">
                            Error loading posts: {postsError.message}
                          </TableCell>
                        </TableRow>
                      ) : !postsData || postsData.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-8">
                            No posts found
                          </TableCell>
                        </TableRow>
                      ) : (
                        postsData.map((post: any) => (
                          <TableRow key={post.id}>
                            <TableCell className="font-medium max-w-xs truncate">
                              {post.title}
                            </TableCell>
                            <TableCell>{post.author_name}</TableCell>
                            <TableCell>
                              <Badge variant="secondary">{post.category}</Badge>
                            </TableCell>
                            <TableCell>
                              {new Date(post.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              <div className="text-sm text-muted-foreground">
                                {post.likes_count} likes, {post.comments_count} replies
                              </div>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setDeletePostDialog(post)}
                                className="text-red-600 hover:text-red-700"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Ban User Dialog */}
        <Dialog open={banDialogOpen} onOpenChange={setBanDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Ban User</DialogTitle>
              <DialogDescription>
                Are you sure you want to ban {selectedUser?.name}? They will not be
                able to login or access the platform.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="ban-reason">Reason for ban *</Label>
                <Textarea
                  id="ban-reason"
                  placeholder="Enter reason for banning this user..."
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  rows={4}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setBanDialogOpen(false);
                  setBanReason("");
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleBanConfirm}
                disabled={!banReason.trim() || banUserMutation.isPending}
              >
                {banUserMutation.isPending ? "Banning..." : "Ban User"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Unban User Dialog */}
        <Dialog open={unbanDialogOpen} onOpenChange={setUnbanDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Unban User</DialogTitle>
              <DialogDescription>
                Are you sure you want to unban {selectedUser?.name}? They will
                regain access to the platform.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setUnbanDialogOpen(false);
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUnbanConfirm}
                disabled={unbanUserMutation.isPending}
              >
                {unbanUserMutation.isPending ? "Unbanning..." : "Unban User"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Post Dialog */}
        <Dialog
          open={!!deletePostDialog}
          onOpenChange={(open) => !open && setDeletePostDialog(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Post</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete "{deletePostDialog?.title}"? This
                action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeletePostDialog(null)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleDeletePost(deletePostDialog.id)}
                disabled={deletePostMutation.isPending}
              >
                {deletePostMutation.isPending ? "Deleting..." : "Delete Post"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Send Notification Dialog */}
        <Dialog open={notificationDialogOpen} onOpenChange={setNotificationDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Send Notification to {selectedUser?.name}</DialogTitle>
              <DialogDescription>
                Send a custom notification to this user. They will receive it in their notifications panel.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="notification-title">Title *</Label>
                <Input
                  id="notification-title"
                  placeholder="Enter notification title..."
                  value={notificationTitle}
                  onChange={(e) => setNotificationTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notification-message">Message *</Label>
                <Textarea
                  id="notification-message"
                  placeholder="Enter notification message..."
                  value={notificationMessage}
                  onChange={(e) => setNotificationMessage(e.target.value)}
                  rows={4}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setNotificationDialogOpen(false);
                  setNotificationTitle("");
                  setNotificationMessage("");
                  setSelectedUser(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendNotification}
                disabled={!notificationTitle.trim() || !notificationMessage.trim() || sendNotificationMutation.isPending}
              >
                {sendNotificationMutation.isPending ? "Sending..." : "Send Notification"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Broadcast Notification Dialog */}
        <Dialog open={broadcastDialogOpen} onOpenChange={setBroadcastDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Broadcast Notification</DialogTitle>
              <DialogDescription>
                Send a notification to all users or selected users.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="broadcast-title">Title *</Label>
                <Input
                  id="broadcast-title"
                  placeholder="Enter notification title..."
                  value={broadcastTitle}
                  onChange={(e) => setBroadcastTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="broadcast-message">Message *</Label>
                <Textarea
                  id="broadcast-message"
                  placeholder="Enter notification message..."
                  value={broadcastMessage}
                  onChange={(e) => setBroadcastMessage(e.target.value)}
                  rows={4}
                />
              </div>

              {/* Toggle between all users and selected users */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="broadcast-all"
                    checked={broadcastToAll}
                    onChange={(e) => {
                      setBroadcastToAll(e.target.checked);
                      if (e.target.checked) {
                        setSelectedUserIds([]);
                      }
                    }}
                    className="h-4 w-4"
                  />
                  <Label htmlFor="broadcast-all" className="cursor-pointer">
                    Send to all users ({usersData?.length || 0} users)
                  </Label>
                </div>
              </div>

              {/* User selection when not broadcasting to all */}
              {!broadcastToAll && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Select Users ({selectedUserIds.length} selected)</Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={toggleAllUsers}
                    >
                      {selectedUserIds.length === usersData?.length ? "Deselect All" : "Select All"}
                    </Button>
                  </div>
                  <div className="border rounded-md max-h-60 overflow-y-auto p-4 space-y-2">
                    {usersData?.map((user: any) => (
                      <div key={user.id} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={`user-${user.id}`}
                          checked={selectedUserIds.includes(user.id)}
                          onChange={() => toggleUserSelection(user.id)}
                          className="h-4 w-4"
                        />
                        <Label htmlFor={`user-${user.id}`} className="cursor-pointer flex-1">
                          {user.name} ({user.phone_number})
                          {user.is_banned && <span className="ml-2 text-xs text-red-600">(Banned)</span>}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setBroadcastDialogOpen(false);
                  setBroadcastTitle("");
                  setBroadcastMessage("");
                  setSelectedUserIds([]);
                  setBroadcastToAll(true);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleBroadcastSend}
                disabled={
                  !broadcastTitle.trim() ||
                  !broadcastMessage.trim() ||
                  (!broadcastToAll && selectedUserIds.length === 0) ||
                  broadcastNotificationMutation.isPending
                }
              >
                {broadcastNotificationMutation.isPending ? "Sending..." : "Send Broadcast"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
}
