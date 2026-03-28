"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { User, Edit2, Shield, Calendar, Phone, MapPin, Globe, Clock, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { Sidebar } from "@/components/layout/Sidebar";
import { Navbar } from "@/components/layout/Navbar";

// Indian states
const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];

// Kerala districts
const KERALA_DISTRICTS = [
  { code: "KL-TVM", name: "Thiruvananthapuram" },
  { code: "KL-KLM", name: "Kollam" },
  { code: "KL-PTA", name: "Pathanamthitta" },
  { code: "KL-ALP", name: "Alappuzha" },
  { code: "KL-KTM", name: "Kottayam" },
  { code: "KL-IDK", name: "Idukki" },
  { code: "KL-EKM", name: "Ernakulam" },
  { code: "KL-TSR", name: "Thrissur" },
  { code: "KL-PKD", name: "Palakkad" },
  { code: "KL-MLP", name: "Malappuram" },
  { code: "KL-KKD", name: "Kozhikode" },
  { code: "KL-WYD", name: "Wayanad" },
  { code: "KL-KNR", name: "Kannur" },
  { code: "KL-KSD", name: "Kasaragod" },
];

interface UserProfile {
  id: string;
  phone_number: string;
  name: string | null;
  role: string;
  state: string | null;
  district: string | null;
  district_name: string | null;
  language: string;
  created_at: string;
}

interface UpdateData {
  name?: string;
  state?: string;
  district?: string;
  language?: string;
}

export default function ProfilePage() {
  const [isEditing, setIsEditing] = useState(false);
  const [showOtpDialog, setShowOtpDialog] = useState(false);
  const [showPhoneChangeDialog, setShowPhoneChangeDialog] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpRequestId, setOtpRequestId] = useState("");
  const [pendingUpdate, setPendingUpdate] = useState<UpdateData>({});
  
  // Phone change states
  const [newPhoneNumber, setNewPhoneNumber] = useState("");
  const [phoneOtp, setPhoneOtp] = useState("");
  const [phoneOtpRequestId, setPhoneOtpRequestId] = useState("");

  // Form state
  const [name, setName] = useState<string>("");
  const [state, setState] = useState<string>("");
  const [district, setDistrict] = useState<string>("");
  const [language, setLanguage] = useState<string>("");

  // Fetch user profile
  const { data: profile, isLoading, refetch } = useQuery<UserProfile>({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data } = await api.get("/users/me");
      return data;
    },
  });

  // Update form when profile loads
  useEffect(() => {
    if (profile) {
      setName(profile.name || "");
      setState(profile.state || "");
      setDistrict(profile.district || "");
      setLanguage(profile.language);
    }
  }, [profile]);

  // Request OTP mutation
  const requestOtpMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/auth/request-otp", {
        phone_number: profile?.phone_number,
      });
      return data;
    },
    onSuccess: (data) => {
      setOtpRequestId(data.request_id);
      setShowOtpDialog(true);
      toast.success("OTP sent to your phone number");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to send OTP");
    },
  });

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: async (data: { otp: string; update: UpdateData }) => {
      // Verify OTP first
      await api.post("/auth/verify-otp", {
        request_id: otpRequestId,
        otp: data.otp,
        phone_number: profile?.phone_number,
      });

      // Then update profile
      const { data: updatedProfile } = await api.put("/users/me", data.update);
      return updatedProfile;
    },
    onSuccess: () => {
      toast.success("Profile updated successfully");
      setShowOtpDialog(false);
      setIsEditing(false);
      setOtp("");
      setOtpRequestId("");
      refetch();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update profile");
    },
  });

  // Request OTP for new phone number
  const requestPhoneOtpMutation = useMutation({
    mutationFn: async (phoneNumber: string) => {
      const { data } = await api.post("/auth/request-otp", {
        phone_number: phoneNumber,
      });
      return data;
    },
    onSuccess: (data) => {
      setPhoneOtpRequestId(data.request_id);
      toast.success("OTP sent to new phone number");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to send OTP");
    },
  });

  // Update phone number mutation
  const updatePhoneMutation = useMutation({
    mutationFn: async (data: { new_phone_number: string; otp: string; request_id: string }) => {
      const { data: updatedProfile } = await api.put("/users/me/phone", data);
      return updatedProfile;
    },
    onSuccess: () => {
      toast.success("Phone number updated successfully");
      setShowPhoneChangeDialog(false);
      setNewPhoneNumber("");
      setPhoneOtp("");
      setPhoneOtpRequestId("");
      refetch();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update phone number");
    },
  });

  const handleEditClick = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    if (profile) {
      setName(profile.name || "");
      setState(profile.state || "");
      setDistrict(profile.district || "");
      setLanguage(profile.language);
    }
  };

  const handleSaveClick = () => {
    const updates: UpdateData = {};
    let hasChanges = false;

    if (name !== profile?.name) {
      updates.name = name;
      hasChanges = true;
    }

    if (state !== profile?.state) {
      updates.state = state;
      hasChanges = true;
    }

    if (district !== profile?.district) {
      updates.district = district;
      hasChanges = true;
    }

    if (language !== profile?.language) {
      updates.language = language;
      hasChanges = true;
    }

    if (!hasChanges) {
      toast.info("No changes to save");
      return;
    }

    setPendingUpdate(updates);
    requestOtpMutation.mutate();
  };

  const handleOtpSubmit = () => {
    if (!otp || otp.length !== 6) {
      toast.error("Please enter a valid 6-digit OTP");
      return;
    }

    updateProfileMutation.mutate({ otp, update: pendingUpdate });
  };

  const handlePhoneChangeClick = () => {
    setShowPhoneChangeDialog(true);
  };

  const handleRequestPhoneOtp = () => {
    if (!newPhoneNumber || newPhoneNumber.length !== 10) {
      toast.error("Please enter a valid 10-digit phone number");
      return;
    }

    if (!/^[6-9]\d{9}$/.test(newPhoneNumber)) {
      toast.error("Please enter a valid Indian mobile number");
      return;
    }

    if (newPhoneNumber === profile?.phone_number) {
      toast.error("New phone number must be different from current");
      return;
    }

    requestPhoneOtpMutation.mutate(newPhoneNumber);
  };

  const handlePhoneOtpSubmit = () => {
    if (!phoneOtp || phoneOtp.length !== 6) {
      toast.error("Please enter a valid 6-digit OTP");
      return;
    }

    if (!phoneOtpRequestId) {
      toast.error("Please request OTP first");
      return;
    }

    updatePhoneMutation.mutate({
      new_phone_number: newPhoneNumber,
      otp: phoneOtp,
      request_id: phoneOtpRequestId,
    });
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen bg-gray-50 dark:bg-black">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Navbar />
          <main className="flex-1 overflow-auto p-6">
            <div className="max-w-4xl mx-auto">
              <Card>
                <CardContent className="p-12">
                  <div className="text-center text-muted-foreground">Loading profile...</div>
                </CardContent>
              </Card>
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gray-50 dark:bg-black">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Navbar />
        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-gradient-to-br from-green-500 to-green-700 flex items-center justify-center text-white shadow-lg">
              <User className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Profile</h1>
              <p className="text-muted-foreground">Manage your personal information</p>
            </div>
          </div>
          {!isEditing && (
            <Button onClick={handleEditClick} className="gap-2 bg-green-600 hover:bg-green-700">
              <Edit2 className="h-4 w-4" />
              Edit Profile
            </Button>
          )}
        </div>

        {/* Profile Card */}
        <Card className="shadow-lg">
          <CardHeader className="border-b bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/20 dark:to-emerald-950/20">
            <CardTitle className="flex items-center gap-2 text-xl">
              <User className="h-6 w-6 text-green-600" />
              Personal Information
            </CardTitle>
            <CardDescription>
              Your account details and preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6 pt-6">
            {/* Name */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <User className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Full Name</Label>
                {isEditing ? (
                  <Input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Enter your name"
                    className="mt-2 h-11"
                    maxLength={100}
                  />
                ) : (
                  <p className="text-xl font-medium mt-1">
                    {profile?.name || <span className="italic text-muted-foreground">Not set</span>}
                  </p>
                )}
              </div>
            </div>

            {/* Phone Number */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <Phone className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Phone Number</Label>
                    <p className="text-xl font-medium mt-1">{profile?.phone_number}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePhoneChangeClick}
                    className="hover:bg-green-50 hover:text-green-700 hover:border-green-300 dark:hover:bg-green-900/20"
                  >
                    Change
                  </Button>
                </div>
              </div>
            </div>

            {/* Role */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Role</Label>
                <p className="text-xl font-medium mt-1 capitalize">{profile?.role}</p>
                {profile?.role === "admin" && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 mt-2">
                    Administrator
                  </span>
                )}
              </div>
            </div>

            {/* State */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg">
                <MapPin className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">State</Label>
                {isEditing ? (
                  <Select value={state} onValueChange={setState}>
                    <SelectTrigger className="mt-2 h-11">
                      <SelectValue placeholder="Select state" />
                    </SelectTrigger>
                    <SelectContent>
                      {INDIAN_STATES.map((stateName) => (
                        <SelectItem key={stateName} value={stateName}>
                          {stateName}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-xl font-medium mt-1">
                    {profile?.state || <span className="italic text-muted-foreground">Not set</span>}
                  </p>
                )}
              </div>
            </div>

            {/* District */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <MapPin className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">District</Label>
                {isEditing ? (
                  <Select value={district} onValueChange={setDistrict}>
                    <SelectTrigger className="mt-2 h-11">
                      <SelectValue placeholder="Select district" />
                    </SelectTrigger>
                    <SelectContent>
                      {KERALA_DISTRICTS.map((d) => (
                        <SelectItem key={d.code} value={d.code}>
                          {d.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-xl font-medium mt-1">
                    {profile?.district_name || (
                      <span className="text-muted-foreground italic">Not set</span>
                    )}
                  </p>
                )}
              </div>
            </div>

            {/* Language */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                <Globe className="h-5 w-5 text-orange-600 dark:text-orange-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Preferred Language</Label>
                {isEditing ? (
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger className="mt-2 h-11">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="en">English</SelectItem>
                      <SelectItem value="ml">Malayalam (മലയാളം)</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <p className="text-xl font-medium mt-1">
                    {language === "en" ? "English" : "Malayalam (മലയാളം)"}
                  </p>
                )}
              </div>
            </div>

            {/* Member Since */}
            <div className="flex items-start gap-4 p-4 rounded-lg border border-border hover:border-green-200 dark:hover:border-green-800 transition-colors">
              <div className="p-2 bg-teal-100 dark:bg-teal-900/30 rounded-lg">
                <Calendar className="h-5 w-5 text-teal-600 dark:text-teal-400" />
              </div>
              <div className="flex-1">
                <Label className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Member Since</Label>
                <p className="text-xl font-medium mt-1">
                  {profile?.created_at
                    ? new Date(profile.created_at).toLocaleDateString("en-IN", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })
                    : "N/A"}
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            {isEditing && (
              <div className="flex gap-3 pt-4 border-t">
                <Button
                  onClick={handleSaveClick}
                  disabled={requestOtpMutation.isPending}
                  className="flex-1 h-11 bg-green-600 hover:bg-green-700"
                >
                  {requestOtpMutation.isPending ? "Sending OTP..." : "Save Changes"}
                </Button>
                <Button
                  onClick={handleCancelEdit}
                  variant="outline"
                  disabled={requestOtpMutation.isPending}
                  className="flex-1 h-11"
                >
                  Cancel
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* OTP Verification Dialog */}
        <Dialog open={showOtpDialog} onOpenChange={setShowOtpDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl">Verify Your Identity</DialogTitle>
              <DialogDescription>
                Enter the 6-digit OTP sent to <span className="font-semibold text-foreground">{profile?.phone_number}</span>
              </DialogDescription>
            </DialogHeader>
            <div className="py-6">
              <Label htmlFor="otp" className="text-sm font-semibold">OTP</Label>
              <Input
                id="otp"
                type="text"
                placeholder="000000"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                className="mt-2 text-center text-3xl tracking-[0.5em] font-bold h-14"
                autoFocus
              />
              <p className="text-xs text-muted-foreground mt-3 text-center flex items-center justify-center gap-2">
                <Clock className="h-3 w-3" />
                OTP expires in 10 minutes
              </p>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                onClick={() => {
                  setShowOtpDialog(false);
                  setOtp("");
                }}
                variant="outline"
                disabled={updateProfileMutation.isPending}
                className="flex-1 sm:flex-none"
              >
                Cancel
              </Button>
              <Button
                onClick={handleOtpSubmit}
                disabled={updateProfileMutation.isPending || otp.length !== 6}
                className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700"
              >
                {updateProfileMutation.isPending ? "Verifying..." : "Verify & Update"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Phone Number Change Dialog */}
        <Dialog open={showPhoneChangeDialog} onOpenChange={setShowPhoneChangeDialog}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle className="text-xl">Change Phone Number</DialogTitle>
              <DialogDescription>
                Enter your new phone number. We'll send you an OTP to verify it.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <Label htmlFor="new-phone" className="text-sm font-semibold">New Phone Number</Label>
                <Input
                  id="new-phone"
                  type="tel"
                  placeholder="9876543210"
                  maxLength={10}
                  value={newPhoneNumber}
                  onChange={(e) => setNewPhoneNumber(e.target.value.replace(/\D/g, ""))}
                  className="mt-2 h-11 text-lg"
                  disabled={!!phoneOtpRequestId}
                  autoFocus
                />
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Phone className="h-3 w-3" />
                  Enter 10-digit Indian mobile number
                </p>
              </div>

              {!phoneOtpRequestId && (
                <Button
                  onClick={handleRequestPhoneOtp}
                  disabled={requestPhoneOtpMutation.isPending}
                  className="w-full h-11 bg-green-600 hover:bg-green-700"
                >
                  {requestPhoneOtpMutation.isPending ? "Sending OTP..." : "Send OTP"}
                </Button>
              )}

              {phoneOtpRequestId && (
                <div className="pt-2">
                  <Label htmlFor="phone-otp" className="text-sm font-semibold">Enter OTP</Label>
                  <Input
                    id="phone-otp"
                    type="text"
                    placeholder="000000"
                    maxLength={6}
                    value={phoneOtp}
                    onChange={(e) => setPhoneOtp(e.target.value.replace(/\D/g, ""))}
                    className="mt-2 text-center text-3xl tracking-[0.5em] font-bold h-14"
                    autoFocus
                  />
                  <p className="text-xs text-green-600 dark:text-green-400 mt-3 text-center flex items-center justify-center gap-2">
                    <CheckCircle2 className="h-3 w-3" />
                    OTP sent to {newPhoneNumber}
                  </p>
                </div>
              )}
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                onClick={() => {
                  setShowPhoneChangeDialog(false);
                  setNewPhoneNumber("");
                  setPhoneOtp("");
                  setPhoneOtpRequestId("");
                }}
                variant="outline"
                disabled={updatePhoneMutation.isPending}
                className="flex-1 sm:flex-none"
              >
                Cancel
              </Button>
              {phoneOtpRequestId && (
                <Button
                  onClick={handlePhoneOtpSubmit}
                  disabled={updatePhoneMutation.isPending || phoneOtp.length !== 6}
                  className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700"
                >
                  {updatePhoneMutation.isPending ? "Updating..." : "Update Phone Number"}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
          </div>
        </main>
      </div>
    </div>
  );
}
