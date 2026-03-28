"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  CalendarDays,
  Leaf,
  LogOut,
  User,
  Loader2,
  Sprout,
  ArrowLeftRight,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { commoditiesService } from "@/services/commodities";
import { inventoryService } from "@/services/inventory";
import { salesService, RecordSaleData } from "@/services/sales";
import { mandisService } from "@/services/mandis";

const mobileMenuItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: ShoppingCart, label: "Commodities", href: "/commodities" },
  { icon: MapPin, label: "Mandis", href: "/mandis" },
  { icon: Package, label: "Inventory", href: "/inventory" },
  { icon: IndianRupee, label: "Sales", href: "/sales" },
  { icon: Truck, label: "Transport", href: "/transport" },
  { icon: TrendingUp, label: "Price Forecast", href: "/forecast" },
  { icon: CalendarDays, label: "Seasonal Calendar", href: "/seasonal" },
  { icon: Sprout, label: "Soil Advisor", href: "/soil-advisor" },
  { icon: BarChart3, label: "Analytics", href: "/analytics" },
  { icon: MessageSquare, label: "Community", href: "/community" },
  { icon: Bell, label: "Notifications", href: "/notifications" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
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

  const queryClient = useQueryClient();

  // Analyze Inventory
  const [isAnalyzeOpen, setIsAnalyzeOpen] = useState(false);
  const analyzeMutation = useMutation({
    mutationFn: inventoryService.analyzeInventory,
    onError: () => toast.error("Failed to analyze inventory"),
  });

  const handleOpenAnalyze = () => {
    setIsAnalyzeOpen(true);
    analyzeMutation.mutate();
  };

  // Record Sale
  const [isRecordSaleOpen, setIsRecordSaleOpen] = useState(false);
  const [saleFormData, setSaleFormData] = useState<RecordSaleData>({
    commodity_id: "",
    quantity: 0,
    unit: "kg",
    price_per_unit: 0,
    buyer_name: "",
    sale_date: new Date().toISOString().split("T")[0],
  });

  const { data: navCommodities } = useQuery({
    queryKey: ["commodities"],
    queryFn: () => commoditiesService.getAll({ limit: 500 }),
    staleTime: 10 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    enabled: isRecordSaleOpen,
  });

  const recordSaleMutation = useMutation({
    mutationFn: salesService.recordSale,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["sales-analytics"] });
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
      setIsRecordSaleOpen(false);
      setSaleFormData({ commodity_id: "", quantity: 0, unit: "kg", price_per_unit: 0, buyer_name: "", sale_date: new Date().toISOString().split("T")[0] });
      toast.success("Sale recorded successfully");
    },
    onError: () => toast.error("Failed to record sale"),
  });

  const handleRecordSaleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!saleFormData.commodity_id || saleFormData.quantity <= 0 || saleFormData.price_per_unit <= 0) return;
    recordSaleMutation.mutate(saleFormData);
  };

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
            <span className="font-bold">AgriProfit</span>
          </Link>

          {/* Search */}
          <div className="hidden md:flex items-center flex-1 max-w-md mx-4" ref={searchRef}>
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search commodities, mandis..."
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
                        Commodities
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
                              {commodity.category || "Commodity"}
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
                        Mandis
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
                    No results found for "{searchQuery}"
                  </div>
                )}
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-2">
            {/* Price Forecast */}
            <Button variant="outline" size="sm" className="gap-1.5 hidden sm:flex" asChild>
              <Link href="/forecast">
                <TrendingUp className="h-4 w-4 text-violet-500" />
                <span className="hidden md:inline">Price Forecast</span>
              </Link>
            </Button>
            {/* Analyze Inventory Dialog */}
            <Button variant="outline" size="sm" className="gap-1.5 hidden sm:flex" onClick={handleOpenAnalyze}>
              <BarChart3 className="h-4 w-4 text-green-600" />
              <span className="hidden md:inline">Analyze Inventory</span>
            </Button>
            <Dialog open={isAnalyzeOpen} onOpenChange={setIsAnalyzeOpen}>
              <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-green-600" /> Inventory Analysis
                  </DialogTitle>
                  <DialogDescription>Best mandis to sell your current stock.</DialogDescription>
                </DialogHeader>
                {analyzeMutation.isPending && (
                  <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin" /> Analyzing your inventory…
                  </div>
                )}
                {analyzeMutation.isError && (
                  <p className="text-center py-8 text-sm text-red-500">Could not load analysis. Please try again.</p>
                )}
                {analyzeMutation.data && (
                  <div className="space-y-4 pt-2">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-lg border p-3 text-center">
                        <p className="text-xs text-muted-foreground">Items analysed</p>
                        <p className="text-2xl font-bold">{analyzeMutation.data.total_items}</p>
                      </div>
                      <div className="rounded-lg border p-3 text-center">
                        <p className="text-xs text-muted-foreground">Est. revenue range</p>
                        <p className="text-lg font-bold text-green-600">
                          ₹{analyzeMutation.data.total_estimated_min_revenue.toLocaleString()} – ₹{analyzeMutation.data.total_estimated_max_revenue.toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {analyzeMutation.data.analysis.length === 0 ? (
                      <p className="text-center text-sm text-muted-foreground py-6">No inventory items to analyse.</p>
                    ) : (
                      analyzeMutation.data.analysis.map((item) => (
                        <div key={item.commodity_id} className="rounded-lg border p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="font-semibold">{item.commodity_name}</div>
                            <span className="text-sm text-muted-foreground">{item.quantity} {item.unit}</span>
                          </div>
                          {item.recommended_mandi && (
                            <div className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
                              <CheckCircle2 className="h-4 w-4" />
                              Best: <span className="font-medium">{item.recommended_mandi}</span>
                              {item.recommended_price && <span className="ml-1">@ ₹{item.recommended_price}/q</span>}
                            </div>
                          )}
                          {item.message && <p className="text-xs text-muted-foreground">{item.message}</p>}
                          {item.best_mandis.length > 0 && (
                            <div className="space-y-1 pt-1">
                              {item.best_mandis.slice(0, 3).map((m) => (
                                <div key={m.mandi_id} className="flex items-center justify-between text-xs rounded bg-muted/40 px-2 py-1">
                                  <span>{m.mandi_name}{m.is_local && <span className="ml-1 text-blue-500">(local)</span>}</span>
                                  <span className="font-medium">
                                    {m.net_profit != null ? <>₹{m.net_profit.toLocaleString()} net</> : <>₹{m.modal_price}/q</>}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                )}
              </DialogContent>
            </Dialog>

            {/* Record Sale Dialog */}
            <Button variant="outline" size="sm" className="gap-1.5 hidden sm:flex" onClick={() => setIsRecordSaleOpen(true)}>
              <IndianRupee className="h-4 w-4 text-amber-600" />
              <span className="hidden md:inline">Record Sale</span>
            </Button>
            <Dialog open={isRecordSaleOpen} onOpenChange={setIsRecordSaleOpen}>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Record New Sale</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleRecordSaleSubmit} className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label>Commodity</Label>
                    <Select
                      value={saleFormData.commodity_id}
                      onValueChange={(v) => setSaleFormData({ ...saleFormData, commodity_id: v })}
                    >
                      <SelectTrigger><SelectValue placeholder="Select commodity" /></SelectTrigger>
                      <SelectContent>
                        {navCommodities?.map((c: any) => (
                          <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Quantity</Label>
                      <Input
                        type="number" min="0.01" step="0.01"
                        value={saleFormData.quantity || ""}
                        onChange={(e) => setSaleFormData({ ...saleFormData, quantity: parseFloat(e.target.value) })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Unit</Label>
                      <Select value={saleFormData.unit} onValueChange={(v) => setSaleFormData({ ...saleFormData, unit: v })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="kg">kg</SelectItem>
                          <SelectItem value="quintal">quintal</SelectItem>
                          <SelectItem value="ton">ton</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Price per unit (₹)</Label>
                    <Input
                      type="number" min="0.01" step="0.01"
                      value={saleFormData.price_per_unit || ""}
                      onChange={(e) => setSaleFormData({ ...saleFormData, price_per_unit: parseFloat(e.target.value) })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Buyer Name (Optional)</Label>
                    <Input
                      value={saleFormData.buyer_name}
                      onChange={(e) => setSaleFormData({ ...saleFormData, buyer_name: e.target.value })}
                      placeholder="e.g. Local Mandi"
                    />
                  </div>
                  <Button type="submit" className="w-full bg-green-600 hover:bg-green-700" disabled={recordSaleMutation.isPending}>
                    {recordSaleMutation.isPending ? "Recording…" : "Confirm Sale"}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
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
              <span className="hidden sm:inline">Log out</span>
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
                <span className="font-bold">AgriProfit</span>
              </Link>
              <button onClick={() => setMobileMenuOpen(false)}>
                <X className="h-5 w-5" />
              </button>
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
                    {item.label}
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
