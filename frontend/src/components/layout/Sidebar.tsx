"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  LayoutDashboard,
  BarChart3,
  MessageSquare,
  Package,
  IndianRupee,
  Bell,
  Leaf,
  ShoppingCart,
  MapPin,
  Truck,
  Shield,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

const menuItems = [
  { icon: LayoutDashboard, labelKey: "dashboard" as const, href: "/dashboard" },
  { icon: ShoppingCart, labelKey: "commodities" as const, href: "/commodities" },
  { icon: MapPin, labelKey: "mandis" as const, href: "/mandis" },
  { icon: Package, labelKey: "inventory" as const, href: "/inventory" },
  { icon: IndianRupee, labelKey: "sales" as const, href: "/sales" },
  { icon: Truck, labelKey: "transport" as const, href: "/transport" },
  { icon: BarChart3, labelKey: "analytics" as const, href: "/analytics" },
  { icon: MessageSquare, labelKey: "community" as const, href: "/community" },
  { icon: Bell, labelKey: "notifications" as const, href: "/notifications" },
];

const adminMenuItem = { icon: Shield, labelKey: "admin" as const, href: "/admin" };

export function Sidebar() {
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);
  const t = useTranslations('sidebar');
  const tc = useTranslations('common');

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      const user = JSON.parse(userData);
      setIsAdmin(user.role === "admin");
    }
  }, []);

  return (
    <aside className="hidden lg:flex w-64 flex-col bg-card border-r border-border min-h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
            <Leaf className="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <span className="text-xl font-bold">{tc('appName')}</span>
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
          {t('mainMenu')}
        </div>
        {menuItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              {t(item.labelKey)}
            </Link>
          );
        })}

        {/* Admin Section */}
        {isAdmin && (
          <>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3 mt-4">
              {t('admin')}
            </div>
            <Link
              href={adminMenuItem.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                pathname === adminMenuItem.href || pathname?.startsWith(adminMenuItem.href + "/")
                  ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <adminMenuItem.icon className="h-5 w-5" />
              {t(adminMenuItem.labelKey)}
            </Link>
          </>
        )}
      </nav>
    </aside>
  );
}
