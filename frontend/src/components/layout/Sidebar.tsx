"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
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
  CalendarDays,
  Shield,
  User,
  Sprout,
  ArrowLeftRight,
  Wheat,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const menuItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: ShoppingCart, label: "Commodities", href: "/commodities" },
  { icon: MapPin, label: "Mandis", href: "/mandis" },
  { icon: Package, label: "Inventory", href: "/inventory" },
  { icon: IndianRupee, label: "Sales", href: "/sales" },
  { icon: Truck, label: "Transport", href: "/transport" },
  { icon: TrendingUp, label: "Price Forecast", href: "/forecast" },
  { icon: CalendarDays, label: "Seasonal Calendar", href: "/seasonal" },
  { icon: Sprout, label: "Soil Advisor", href: "/soil-advisor" },
  { icon: Wheat, label: "Harvest Advisor", href: "/harvest-advisor" },
  { icon: BarChart3, label: "Market Research", href: "/analytics" },
  { icon: MessageSquare, label: "Community", href: "/community" },
  { icon: Bell, label: "Notifications", href: "/notifications" },
];

const adminMenuItem = { icon: Shield, label: "Admin", href: "/admin" };

export function Sidebar() {
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);

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
          <span className="text-xl font-bold">AgriProfit</span>
        </Link>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3">
          Main Menu
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
              {item.label}
            </Link>
          );
        })}

        {/* Admin Section */}
        {isAdmin && (
          <>
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-3 mt-4">
              Admin
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
              {adminMenuItem.label}
            </Link>
          </>
        )}
      </nav>
    </aside>
  );
}
