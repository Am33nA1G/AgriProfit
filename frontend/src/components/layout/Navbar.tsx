"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Menu,
  X,
  Search,
  Bell,
  LayoutDashboard,
  ShoppingCart,
  MapPin,
  BarChart3,
  MessageSquare,
  Package,
  IndianRupee,
  Truck,
  Leaf,
  LogOut,
  User,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { commoditiesService } from "@/services/commodities";
import { mandisService } from "@/services/mandis";
import LanguageSwitcher from "@/components/LanguageSwitcher";

const mobileMenuItems = [
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

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const tn = useTranslations('nav');
  const tc = useTranslations('common');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ commodities: any[], mandis: any[] }>({ commodities: [], mandis: [] });
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  // Close search results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery.trim().length > 1) {
        setIsSearching(true);
        try {
          const [commodities, mandis] = await Promise.all([
            commoditiesService.search(searchQuery, 5).catch(() => []),
            mandisService.search(searchQuery, 5).catch(() => [])
          ]);
          setSearchResults({ commodities, mandis });
          setShowResults(true);
        } catch (error) {
          console.error("Search error:", error);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults({ commodities: [], mandis: [] });
        setShowResults(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/login');
  };

  return (
    <>
      <nav className="sticky top-0 z-40 bg-card/95 backdrop-blur border-b border-border">
        <div className="flex items-center justify-between px-4 py-3">
          {/* Mobile Menu Button */}
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-muted"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          {/* Mobile Logo */}
          <Link href="/dashboard" className="lg:hidden flex items-center gap-2">
            <Leaf className="h-6 w-6 text-green-600" />
            <span className="font-bold">{tc('appName')}</span>
          </Link>

          {/* Search */}
          <div className="hidden md:flex items-center flex-1 max-w-md mx-4" ref={searchRef}>
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder={tn('searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => searchQuery.trim().length > 1 && setShowResults(true)}
                className="w-full pl-10 pr-4 py-2 rounded-lg bg-muted/50 border border-border focus:outline-none focus:ring-2 focus:ring-green-500 text-sm"
              />
              {isSearching && (
                <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
              )}

              {/* Search Results Dropdown */}
              {showResults && (searchResults.commodities.length > 0 || searchResults.mandis.length > 0) && (
                <div className="absolute top-full mt-2 w-full bg-card border border-border rounded-lg shadow-lg max-h-96 overflow-y-auto z-50">
                  {/* Commodities Section */}
                  {searchResults.commodities.length > 0 && (
                    <div className="border-b border-border">
                      <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">
                        {tc('commodities')}
                      </div>
                      {searchResults.commodities.map((commodity: any) => (
                        <Link
                          key={commodity.id}
                          href={`/commodities/${commodity.id}`}
                          onClick={() => {
                            setShowResults(false);
                            setSearchQuery("");
                          }}
                          className="flex items-center gap-3 px-3 py-2.5 hover:bg-muted/50 transition-colors cursor-pointer border-b border-border/50 last:border-0"
                        >
                          <ShoppingCart className="h-4 w-4 text-green-600 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate">{commodity.name}</p>
                            <p className="text-xs text-muted-foreground truncate">
                              {commodity.category || tc('commodity')}
                            </p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}

                  {/* Mandis Section */}
                  {searchResults.mandis.length > 0 && (
                    <div>
                      <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">
                        {tc('mandis')}
                      </div>
                      {searchResults.mandis.map((mandi: any) => (
                        <Link
                          key={mandi.id}
                          href={`/mandis/${mandi.id}`}
                          onClick={() => {
                            setShowResults(false);
                            setSearchQuery("");
                          }}
                          className="flex items-center gap-3 px-3 py-2.5 hover:bg-muted/50 transition-colors cursor-pointer border-b border-border/50 last:border-0"
                        >
                          <MapPin className="h-4 w-4 text-blue-600 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm truncate">{mandi.name}</p>
                            <p className="text-xs text-muted-foreground truncate">
                              {mandi.district}, {mandi.state}
                            </p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* No Results Message */}
              {showResults && searchQuery.trim().length > 1 && !isSearching &&
               searchResults.commodities.length === 0 && searchResults.mandis.length === 0 && (
                <div className="absolute top-full mt-2 w-full bg-card border border-border rounded-lg shadow-lg p-4 text-center text-sm text-muted-foreground z-50">
                  {tc('noResultsFor', { query: searchQuery })}
                </div>
              )}
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            <div className="hidden sm:block">
              <LanguageSwitcher />
            </div>
            <Link href="/profile">
              <Avatar className="h-8 w-8 cursor-pointer hover:ring-2 hover:ring-green-500 transition-all">
                <AvatarFallback className="bg-green-600 text-white">
                  <User className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
            </Link>
            <Link href="/notifications">
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
              </Button>
            </Link>
            <Button
              variant="ghost"
              onClick={handleLogout}
              className="gap-2"
            >
              <LogOut className="h-5 w-5" />
              <span className="hidden sm:inline">{tn('logout')}</span>
            </Button>
          </div>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 z-50 bg-black/50"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div
            className="absolute left-0 top-0 h-full w-64 bg-card shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-border flex items-center justify-between">
              <Link href="/dashboard" className="flex items-center gap-2">
                <Leaf className="h-6 w-6 text-green-600" />
                <span className="font-bold">{tc('appName')}</span>
              </Link>
              <button onClick={() => setMobileMenuOpen(false)}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="px-4 pt-3 pb-2 border-b border-border">
              <LanguageSwitcher />
            </div>
            <nav className="p-4 space-y-1">
              {mobileMenuItems.map((item) => {
                const isActive = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                      isActive
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {tn(item.labelKey)}
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
