"use client";

import React, { useState, useMemo, useEffect } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Loader2,
  RefreshCw,
  Store,
  MapPin,
  Scale,
  X,
  Search,
  ChevronDown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AppLayout } from "@/components/layout/AppLayout";
import { analyticsService, DashboardData } from "@/services/analytics";
import { pricesService } from "@/services/prices";
import { mandisService } from "@/services/mandis";
import { commoditiesService } from "@/services/commodities";
import { toast } from "sonner";

// Dynamic imports for recharts
const LineChart = dynamic(() => import("recharts").then((mod) => mod.LineChart), { ssr: false });
const Line = dynamic(() => import("recharts").then((mod) => mod.Line), { ssr: false });
const BarChartComponent = dynamic(() => import("recharts").then((mod) => mod.BarChart), { ssr: false });
const Bar = dynamic(() => import("recharts").then((mod) => mod.Bar), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((mod) => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((mod) => mod.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((mod) => mod.Tooltip), { ssr: false });
const Legend = dynamic(() => import("recharts").then((mod) => mod.Legend), { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then((mod) => mod.ResponsiveContainer), { ssr: false });

const CHART_COLORS = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316", "#A855F7", "#22D3EE"];
const COMMODITIES = [
  // Grains & Cereals
  "Rice", "Wheat", "Maize", "Bajra", "Jowar", "Barley", "Ragi",
  // Pulses
  "Arhar Dal", "Chana Dal", "Moong Dal", "Urad Dal", "Masur Dal",
  // Vegetables
  "Tomato", "Potato", "Onion", "Brinjal", "Cabbage", "Cauliflower", "Carrot", "Beans", "Peas", "Capsicum",
  // Fruits
  "Banana", "Apple", "Mango", "Orange", "Grapes", "Papaya", "Guava",
  // Spices
  "Pepper", "Cardamom", "Turmeric", "Ginger", "Garlic", "Chilli", "Coriander", "Cumin",
  // Cash Crops
  "Coconut", "Rubber", "Coffee", "Tea", "Sugarcane", "Cotton", "Groundnut", "Mustard"
];

// Price Trends Tab - Enhanced with searchable dropdown
function PriceTrendsTab({ dashboardData, pricesData, isLoading }: { dashboardData: DashboardData | undefined; pricesData: any; isLoading: boolean }) {
  const [timeRange, setTimeRange] = useState<"7" | "14" | "30" | "90">("30");
  const [selectedCommodities, setSelectedCommodities] = useState<string[]>(["Rice", "Wheat", "Tomato"]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [displayCount, setDisplayCount] = useState(20);

  // Fetch all commodities from API
  const { data: allCommodities } = useQuery({
    queryKey: ["all-commodities"],
    queryFn: () => commoditiesService.getAll({ limit: 500 }),
    staleTime: 300000, // Cache for 5 minutes
  });

  const commodityNames = useMemo(() => {
    return allCommodities?.map((c: any) => c.name) || COMMODITIES;
  }, [allCommodities]);

  const filteredCommodities = useMemo(() => {
    if (!searchQuery) return commodityNames; // Show all commodities
    return commodityNames.filter((c: string) =>
      c.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [commodityNames, searchQuery]);

  const toggleCommodity = (commodity: string) => {
    if (selectedCommodities.includes(commodity)) {
      if (selectedCommodities.length > 1) {
        setSelectedCommodities(selectedCommodities.filter(c => c !== commodity));
      }
    } else if (selectedCommodities.length < 6) {
      setSelectedCommodities([...selectedCommodities, commodity]);
    } else {
      toast.error("Maximum 6 commodities can be selected");
    }
  };

  const removeCommodity = (commodity: string) => {
    if (selectedCommodities.length > 1) {
      setSelectedCommodities(selectedCommodities.filter(c => c !== commodity));
    }
  };

  // Fetch real historical price data for selected commodities
  const { data: historicalData, isLoading: histLoading } = useQuery({
    queryKey: ["price-trends-historical", selectedCommodities, timeRange],
    queryFn: async () => {
      const results = await Promise.all(
        selectedCommodities.map(async (commodity) => {
          try {
            const response = await pricesService.getHistoricalPrices({
              commodity,
              mandi_id: "all",
              days: parseInt(timeRange),
            });
            return { commodity, data: response.data || [] };
          } catch {
            return { commodity, data: [] };
          }
        })
      );
      return results;
    },
    staleTime: 60000,
  });

  const priceTrendsData = useMemo(() => {
    if (!historicalData) return [];

    // Build a date -> commodity prices map
    const dateMap: Record<string, Record<string, number>> = {};
    for (const { commodity, data } of historicalData) {
      for (const point of data) {
        const dateStr = new Date(point.date).toLocaleDateString("en-IN", { month: "short", day: "numeric" });
        if (!dateMap[point.date]) dateMap[point.date] = { _raw: 0 } as any;
        (dateMap[point.date] as any)._raw = point.date;
        dateMap[point.date][commodity] = point.price;
      }
    }

    // Sort by raw date and format
    return Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([rawDate, values]) => {
        const entry: Record<string, string | number> = {
          date: new Date(rawDate).toLocaleDateString("en-IN", { month: "short", day: "numeric" }),
        };
        for (const commodity of selectedCommodities) {
          if (values[commodity] !== undefined) {
            entry[commodity] = values[commodity];
          }
        }
        return entry;
      });
  }, [historicalData, selectedCommodities]);

  // Fetch real current prices for the price table
  const { data: currentPricesForTable } = useQuery({
    queryKey: ["analytics-current-prices"],
    queryFn: () => pricesService.getCurrentPrices(),
    staleTime: 60000,
  });

  const allCommoditiesData = useMemo(() => {
    const prices = currentPricesForTable?.prices || [];
    return prices.slice(0, displayCount).map((p: any) => ({
      name: p.commodity,
      category: "Market",
      currentPrice: p.price_per_quintal || 0,
      minPrice: p.min_price || (p.price_per_quintal || 0) * 0.95,
      maxPrice: p.max_price || (p.price_per_quintal || 0) * 1.05,
      change: p.change_percent || 0,
      volume: null,
      mandi: p.mandi_name || "N/A",
    }));
  }, [currentPricesForTable, displayCount]);

  const totalCommodities = currentPricesForTable?.prices?.length || 0;
  const hasMore = displayCount < totalCommodities;
  const loadMore = () => setDisplayCount(prev => Math.min(prev + 20, totalCommodities));

  if (isLoading || histLoading) return <div className="space-y-4"><Skeleton className="h-64 w-full" /><Skeleton className="h-32 w-full" /></div>;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              Price Trends (Last {timeRange} Days)
            </CardTitle>
            <div className="flex items-center gap-2">
              <Label className="text-sm text-muted-foreground">Time Range:</Label>
              <Select value={timeRange} onValueChange={(v: "7" | "14" | "30" | "90") => setTimeRange(v)}>
                <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 Days</SelectItem>
                  <SelectItem value="14">14 Days</SelectItem>
                  <SelectItem value="30">30 Days</SelectItem>
                  <SelectItem value="90">90 Days</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Selected Commodities Tags */}
          <div className="flex flex-wrap gap-2 mt-3">
            {selectedCommodities.map((c, i) => (
              <Badge key={c} className="px-3 py-1 text-sm" style={{ backgroundColor: CHART_COLORS[i] }}>
                {c}
                <button onClick={() => removeCommodity(c)} className="ml-2 hover:opacity-70">
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>

          {/* Searchable Dropdown */}
          <div className="mt-3 relative">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder={`Search ${commodityNames.length} commodities... (Select up to 6)`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => setIsDropdownOpen(true)}
                className="pl-10 pr-10"
              />
              <ChevronDown
                className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 cursor-pointer"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              />
            </div>
            {isDropdownOpen && (
              <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-md max-h-64 overflow-y-auto">
                {filteredCommodities.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-muted-foreground">No commodities found</div>
                ) : (
                  filteredCommodities.map((c: string) => (
                    <div
                      key={c}
                      className={`relative flex cursor-pointer select-none items-center justify-between rounded-sm px-3 py-2 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground ${selectedCommodities.includes(c) ? "bg-accent/50 text-accent-foreground" : ""}`}
                      onClick={() => {
                        toggleCommodity(c);
                        setSearchQuery("");
                      }}
                    >
                      <span>{c}</span>
                      {selectedCommodities.includes(c) && (
                        <Badge variant="outline" className="bg-green-100 text-green-700 border-green-300">Selected</Badge>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
          {isDropdownOpen && (
            <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)} />
          )}
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceTrendsData}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={timeRange === "90" ? 6 : timeRange === "30" ? 3 : 1} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${v.toFixed(0)}`} />
                <Tooltip formatter={(value) => value != null ? [`₹${Number(value).toFixed(2)}`, ""] : ["", ""]} />
                <Legend />
                {selectedCommodities.map((c, i) => <Line key={c} type="monotone" dataKey={c} stroke={CHART_COLORS[i]} strokeWidth={2} dot={timeRange !== "90"} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Current Prices</span>
            <Badge variant="outline" className="font-normal">{allCommoditiesData.length} commodities</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Commodity</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Mandi</TableHead>
                  <TableHead className="text-right">Min Price</TableHead>
                  <TableHead className="text-right">Current Price</TableHead>
                  <TableHead className="text-right">Max Price</TableHead>
                  <TableHead className="text-right">Volume (Q)</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allCommoditiesData.map((item, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{item.name}</TableCell>
                    <TableCell><Badge variant="outline" className="text-xs">{item.category}</Badge></TableCell>
                    <TableCell className="text-muted-foreground">{item.mandi}</TableCell>
                    <TableCell className="text-right text-blue-600">₹{(item.minPrice || 0).toFixed(2)}</TableCell>
                    <TableCell className="text-right font-semibold">₹{(item.currentPrice || 0).toFixed(2)}</TableCell>
                    <TableCell className="text-right text-orange-600">₹{(item.maxPrice || 0).toFixed(2)}</TableCell>
                    <TableCell className="text-right">{item.volume ?? "N/A"}</TableCell>
                    <TableCell className="text-right">
                      <span className={item.change >= 0 ? "text-green-600" : "text-red-600"}>
                        {item.change >= 0 ? <TrendingUp className="inline h-3 w-3 mr-1" /> : <TrendingDown className="inline h-3 w-3 mr-1" />}
                        {Math.abs(item.change).toFixed(1)}%
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {hasMore && (
            <div className="flex justify-center mt-4">
              <Button
                variant="outline"
                onClick={loadMore}
                className="px-8"
              >
                <Loader2 className="h-4 w-4 mr-2" />
                Load More ({displayCount} of {totalCommodities})
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Mandi Performance Tab
function MandiPerformanceTab({ dashboardData, isLoading }: { dashboardData: DashboardData | undefined; isLoading: boolean }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [facilityFilter, setFacilityFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"name" | "rating">("name");
  
  const { data: mandisData, isLoading: mandisLoading } = useQuery({ 
    queryKey: ["mandis-analytics"], 
    queryFn: () => mandisService.getAll({ limit: 100 }), 
    staleTime: 60000 
  });

  const { data: statesData } = useQuery({
    queryKey: ["mandi-states"],
    queryFn: () => mandisService.getStates(),
    staleTime: 300000,
  });
  
  const filteredMandis = useMemo(() => {
    let filtered = mandisData?.filter((m: any) => {
      const matchesSearch = m.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                           m.district.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesState = stateFilter === "all" || m.state === stateFilter;
      return matchesSearch && matchesState;
    }) || [];

    // Sort mandis
    if (sortBy === "rating") {
      filtered = [...filtered].sort((a: any, b: any) => (b.rating || 0) - (a.rating || 0));
    } else {
      filtered = [...filtered].sort((a: any, b: any) => a.name.localeCompare(b.name));
    }

    return filtered;
  }, [mandisData, searchQuery, stateFilter, sortBy]);

  // Use real mandi data for the bar chart - showing top mandis by listing count
  const mandiData = useMemo(() => {
    if (!mandisData) return [];
    return mandisData
      .slice(0, 5)
      .map((m: any) => ({ name: m.name, volume: m.commodities_accepted?.length || 0 }));
  }, [mandisData]);

  // Statistics
  const stats = useMemo(() => {
    if (!mandisData) return { total: 0, avgRating: 0, states: 0 };
    const ratings = mandisData.filter((m: any) => m.rating).map((m: any) => m.rating);
    const uniqueStates = new Set(mandisData.map((m: any) => m.state));
    return {
      total: mandisData.length,
      avgRating: ratings.length > 0 ? ratings.reduce((a: number, b: number) => a + b, 0) / ratings.length : 0,
      states: uniqueStates.size,
      withFacilities: mandisData.filter((m: any) => m.facilities && Object.values(m.facilities).some(f => f)).length
    };
  }, [mandisData]);

  if (isLoading || mandisLoading) return <div className="space-y-4"><Skeleton className="h-64 w-full" /><Skeleton className="h-64 w-full" /></div>;

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Mandis</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Store className="h-8 w-8 text-blue-600 opacity-75" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">States Covered</p>
                <p className="text-2xl font-bold">{stats.states}</p>
              </div>
              <MapPin className="h-8 w-8 text-green-600 opacity-75" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Avg Rating</p>
                <p className="text-2xl font-bold">{stats.avgRating.toFixed(1)}/5</p>
              </div>
              <BarChart3 className="h-8 w-8 text-yellow-600 opacity-75" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">With Facilities</p>
                <p className="text-2xl font-bold">{stats.withFacilities}</p>
              </div>
              <Store className="h-8 w-8 text-purple-600 opacity-75" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Store className="h-5 w-5 text-blue-600" />Top Mandis by Volume</CardTitle></CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChartComponent data={mandiData}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="volume" fill="#3B82F6" radius={[4, 4, 0, 0]} /></BarChartComponent>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <CardTitle>All Mandis ({filteredMandis.length})</CardTitle>
            <div className="flex flex-col sm:flex-row gap-2">
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input placeholder="Search mandis..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9" />
              </div>
              <Select value={stateFilter} onValueChange={setStateFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="All States" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All States</SelectItem>
                  {statesData?.map((state) => (
                    <SelectItem key={state} value={state}>{state}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={(value) => setSortBy(value as "name" | "rating")}>
                <SelectTrigger className="w-full sm:w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="rating">Rating</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredMandis.slice(0, 12).map((m: any) => (
              <div key={m.id} className="p-4 border rounded-lg hover:shadow-md transition-shadow bg-white">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-lg">{m.name}</h4>
                  {m.rating && (
                    <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                      ⭐ {m.rating.toFixed(1)}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-gray-600 flex items-center gap-1 mb-2">
                  <MapPin className="h-3 w-3" />
                  {m.district}, {m.state}
                </p>
                {m.market_code && (
                  <p className="text-xs text-gray-500 mb-2">Code: {m.market_code}</p>
                )}
                
                {/* Facilities */}
                {m.facilities && Object.values(m.facilities).some((f: any) => f) && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {m.facilities.weighbridge && <Badge variant="outline" className="text-xs">Weighbridge</Badge>}
                    {m.facilities.storage && <Badge variant="outline" className="text-xs">Storage</Badge>}
                    {m.facilities.cold_storage && <Badge variant="outline" className="text-xs">Cold Storage</Badge>}
                    {m.facilities.loading_dock && <Badge variant="outline" className="text-xs">Loading Dock</Badge>}
                  </div>
                )}

                {/* Contact Info */}
                {(m.contact?.phone || m.contact?.email) && (
                  <div className="text-xs text-gray-500 mt-2 space-y-1">
                    {m.contact.phone && <p>📞 {m.contact.phone}</p>}
                    {m.contact.email && <p>✉️ {m.contact.email}</p>}
                  </div>
                )}

                {/* Operating Hours */}
                {m.operating_hours?.opening_time && (
                  <p className="text-xs text-gray-500 mt-2">
                    🕒 {m.operating_hours.opening_time} - {m.operating_hours.closing_time || "N/A"}
                  </p>
                )}

                {/* Commodities Count */}
                {m.commodities_accepted && m.commodities_accepted.length > 0 && (
                  <p className="text-xs text-blue-600 mt-2">
                    {m.commodities_accepted.length} commodities accepted
                  </p>
                )}
              </div>
            ))}
          </div>
          {filteredMandis.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No mandis found matching your filters
            </div>
          )}
          {filteredMandis.length > 12 && (
            <div className="mt-4 text-center text-sm text-gray-500">
              Showing 12 of {filteredMandis.length} mandis
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Crop Comparison Tab
function CropComparisonTab() {
  const [selectedCrops, setSelectedCrops] = useState<string[]>(["Wheat", "Rice"]);
  const [cropSearchQuery, setCropSearchQuery] = useState("");
  const [selectedMandiId, setSelectedMandiId] = useState<string>("");
  const [mandiSearchQuery, setMandiSearchQuery] = useState("");
  const [isMandiDropdownOpen, setIsMandiDropdownOpen] = useState(false);
  const [isCropDropdownOpen, setIsCropDropdownOpen] = useState(false);
  
  // Fetch all commodities from API
  const { data: allCommoditiesForCompare } = useQuery({
    queryKey: ["all-commodities-compare"],
    queryFn: () => commoditiesService.getAll({ limit: 500 }),
    staleTime: 300000, // Cache for 5 minutes
  });

  // Fetch all mandis for selection
  const { data: allMandis } = useQuery({
    queryKey: ["all-mandis-compare"],
    queryFn: () => mandisService.getAll({ limit: 100 }),
    staleTime: 300000,
  });

  // Fetch prices for selected mandi
  const { data: mandiPrices, isLoading: pricesLoading } = useQuery({
    queryKey: ["mandi-prices", selectedMandiId],
    queryFn: async () => {
      if (!selectedMandiId) return [];
      const response = await pricesService.getPricesByMandi(selectedMandiId);
      return response;
    },
    enabled: !!selectedMandiId,
    staleTime: 60000,
  });

  const allCropNames = useMemo(() => {
    return allCommoditiesForCompare?.map((c: any) => c.name) || COMMODITIES;
  }, [allCommoditiesForCompare]);

  const filteredCrops = useMemo(() => {
    let availableCrops = allCropNames;
    
    // If a mandi is selected and we have price data, only show crops with data for that mandi
    if (selectedMandiId && mandiPrices && mandiPrices.length > 0) {
      const commodityIdsWithPrices = new Set(mandiPrices.map((p: any) => p.commodity_id));
      availableCrops = allCropNames.filter((cropName: string) => {
        const commodity = allCommoditiesForCompare?.find((c: any) => 
          c.name === cropName || c.name.toLowerCase() === cropName.toLowerCase()
        );
        return commodity && commodityIdsWithPrices.has(commodity.id);
      });
    }
    
    // Apply search filter
    if (!cropSearchQuery) return availableCrops;
    return availableCrops.filter((c: string) =>
      c.toLowerCase().includes(cropSearchQuery.toLowerCase())
    );
  }, [allCropNames, cropSearchQuery, selectedMandiId, mandiPrices, allCommoditiesForCompare]);

  const filteredMandis = useMemo(() => {
    if (!mandiSearchQuery) return allMandis || [];
    return (allMandis || []).filter((m: any) =>
      m.name.toLowerCase().includes(mandiSearchQuery.toLowerCase()) ||
      m.district.toLowerCase().includes(mandiSearchQuery.toLowerCase())
    );
  }, [allMandis, mandiSearchQuery]);

  // Create comparison data from real prices
  const comparisonData = useMemo(() => {
    if (!selectedMandiId || !mandiPrices) {
      // Return placeholder data when no mandi is selected
      return selectedCrops.map((crop) => ({
        crop,
        avgPrice: null,
        minPrice: null,
        maxPrice: null,
        priceChange: null,
        unit: "kg",
        asOf: null,
        noData: true
      }));
    }

    // Debug logging
    console.log('[Price Comparison] Selected crops:', selectedCrops);
    console.log('[Price Comparison] All commodities:', allCommoditiesForCompare);
    console.log('[Price Comparison] Mandi prices:', mandiPrices);

    // Map selected crops to their price data
    return selectedCrops.map((crop) => {
      // Try exact match first
      let commodity = allCommoditiesForCompare?.find((c: any) => c.name === crop);
      
      // If not found, try case-insensitive match
      if (!commodity) {
        commodity = allCommoditiesForCompare?.find((c: any) => 
          c.name.toLowerCase() === crop.toLowerCase()
        );
      }

      const commodityId = commodity?.id;
      console.log(`[Price Comparison] Crop: ${crop}, Commodity ID: ${commodityId}`);

      if (!commodityId) {
        console.warn(`[Price Comparison] No commodity ID found for crop: ${crop}`);
        return {
          crop,
          avgPrice: null,
          minPrice: null,
          maxPrice: null,
          priceChange: null,
          unit: "kg",
          asOf: null,
          noData: true
        };
      }

      const priceRecord = mandiPrices.find((p: any) => p.commodity_id === commodityId);
      console.log(`[Price Comparison] Price record for ${crop}:`, priceRecord);

      if (!priceRecord) {
        return {
          crop,
          avgPrice: null,
          minPrice: null,
          maxPrice: null,
          priceChange: null,
          unit: "kg",
          asOf: null,
          noData: true
        };
      }

      return {
        crop,
        avgPrice: priceRecord.modal_price,
        minPrice: priceRecord.min_price,
        maxPrice: priceRecord.max_price,
        priceChange: null, // Backend doesn't provide this
        unit: "kg", // Backend doesn't provide this
        asOf: priceRecord.price_date,
        noData: false
      };
    });
  }, [selectedCrops, mandiPrices, selectedMandiId, allCommoditiesForCompare]);

  const selectedMandi = useMemo(() => {
    return allMandis?.find((m: any) => m.id === selectedMandiId);
  }, [allMandis, selectedMandiId]);

  // Filter out selected crops that don't have data in the newly selected mandi
  useEffect(() => {
    if (selectedMandiId && mandiPrices && mandiPrices.length > 0 && allCommoditiesForCompare) {
      const commodityIdsWithPrices = new Set(mandiPrices.map((p: any) => p.commodity_id));
      
      setSelectedCrops((prevCrops) => {
        const validCrops = prevCrops.filter((cropName: string) => {
          const commodity = allCommoditiesForCompare.find((c: any) => 
            c.name === cropName || c.name.toLowerCase() === cropName.toLowerCase()
          );
          return commodity && commodityIdsWithPrices.has(commodity.id);
        });
        
        if (validCrops.length !== prevCrops.length) {
          if (validCrops.length === 0) {
            toast.info("Selected crops don't have data for this mandi. Please select new crops.");
          } else if (validCrops.length < prevCrops.length) {
            toast.info(`Some crops were removed as they don't have data for this mandi.`);
          }
        }
        
        return validCrops;
      });
    }
  }, [selectedMandiId, mandiPrices, allCommoditiesForCompare]);
  
  const addCrop = (crop: string) => {
    if (!selectedCrops.includes(crop)) {
      if (selectedCrops.length < 5) {
        setSelectedCrops([...selectedCrops, crop]);
        setCropSearchQuery("");
        setIsCropDropdownOpen(false);
      } else {
        toast.error("Maximum 5 crops can be compared");
      }
    }
  };

  const removeCrop = (crop: string) => {
    setSelectedCrops(selectedCrops.filter((c) => c !== crop));
  };

  const selectMandi = (mandiId: string) => {
    setSelectedMandiId(mandiId);
    setMandiSearchQuery("");
    setIsMandiDropdownOpen(false);
  };

  const toggleMandiDropdown = () => {
    setIsMandiDropdownOpen(!isMandiDropdownOpen);
    if (!isMandiDropdownOpen) {
      setMandiSearchQuery("");
    }
  };

  const toggleCropDropdown = () => {
    setIsCropDropdownOpen(!isCropDropdownOpen);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Scale className="h-5 w-5 text-purple-600" />Compare Crops</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {/* Mandi Selection */}
          <div>
            <Label htmlFor="mandi-select">Select Mandi</Label>
            <div className="relative mt-2">
              <div className="flex gap-2">
                <Input
                  id="mandi-select"
                  type="text"
                  placeholder={selectedMandi ? `${selectedMandi.name} - ${selectedMandi.district}` : "Search and select a mandi..."}
                  value={mandiSearchQuery}
                  onChange={(e) => {
                    setMandiSearchQuery(e.target.value);
                    setIsMandiDropdownOpen(true);
                  }}
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={toggleMandiDropdown}
                  className="shrink-0"
                >
                  <ChevronDown className={`h-4 w-4 transition-transform ${isMandiDropdownOpen ? 'rotate-180' : ''}`} />
                </Button>
              </div>
              {(isMandiDropdownOpen || mandiSearchQuery) && filteredMandis.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-auto">
                  {filteredMandis.slice(0, 50).map((mandi: any) => (
                    <div
                      key={mandi.id}
                      className="px-4 py-2 hover:bg-gray-100 cursor-pointer border-b last:border-0"
                      onClick={() => selectMandi(mandi.id)}
                    >
                      <div className="font-medium">{mandi.name}</div>
                      <div className="text-sm text-gray-500">{mandi.district}, {mandi.state}</div>
                    </div>
                  ))}
                  {filteredMandis.length > 50 && (
                    <div className="px-4 py-2 text-sm text-gray-500 text-center">
                      Showing first 50 results. Refine your search for more.
                    </div>
                  )}
                </div>
              )}
            </div>
            {selectedMandi && (
              <div className="mt-2">
                <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                  📍 {selectedMandi.name} - {selectedMandi.district}, {selectedMandi.state}
                  <button
                    onClick={() => setSelectedMandiId("")}
                    className="ml-2 hover:text-red-600"
                    aria-label="Clear mandi selection"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              </div>
            )}
          </div>

          {/* Crop Selection */}
          <div>
            <Label htmlFor="crop-select">Select Crops to Compare (max 5)</Label>
            {selectedMandiId && mandiPrices && (
              <p className="text-xs text-muted-foreground mt-1">
                Showing only crops with available price data for {selectedMandi?.name || "this mandi"}
              </p>
            )}
            <div className="relative mt-2">
              <div className="flex gap-2">
                <Input
                  id="crop-select"
                  type="text"
                  placeholder="Search and select crops..."
                  value={cropSearchQuery}
                  onChange={(e) => {
                    setCropSearchQuery(e.target.value);
                    setIsCropDropdownOpen(true);
                  }}
                  className="flex-1"
                />
                <Button
                  variant="outline"
                  size="icon"
                  onClick={toggleCropDropdown}
                  className="shrink-0"
                >
                  <ChevronDown className={`h-4 w-4 transition-transform ${isCropDropdownOpen ? 'rotate-180' : ''}`} />
                </Button>
              </div>
              {(isCropDropdownOpen || cropSearchQuery) && (
                <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg max-h-60 overflow-auto">
                  {filteredCrops.length > 0 ? (
                    <>
                      {filteredCrops.slice(0, 50).map((crop) => (
                        <div
                          key={crop}
                          className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                          onClick={() => {
                            addCrop(crop);
                            setIsCropDropdownOpen(false);
                          }}
                        >
                          {crop}
                        </div>
                      ))}
                      {filteredCrops.length > 50 && (
                        <div className="px-4 py-2 text-sm text-gray-500 text-center">
                          Showing first 50 results. Refine your search for more.
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="px-4 py-3 text-sm text-gray-500 text-center">
                      {selectedMandiId 
                        ? "No crops with price data found for this mandi" 
                        : "No crops found matching your search"}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          
          {selectedCrops.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {selectedCrops.map((crop) => (
                <Badge key={crop} variant="default" className="bg-purple-600 px-3 py-1.5 text-sm">
                  {crop}
                  <button
                    onClick={() => removeCrop(crop)}
                    className="ml-2 hover:text-red-200"
                    aria-label={`Remove ${crop}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      {selectedCrops.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>
              {selectedMandi ? `Price Comparison at ${selectedMandi.name}` : "Select a mandi to view prices"}
            </CardTitle>
            {selectedMandi && !pricesLoading && (
              <CardDescription>
                Showing prices from {selectedMandi.name}, {selectedMandi.district}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            {!selectedMandiId ? (
              <div className="text-center py-8 text-gray-500">
                <Store className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>Please select a mandi to view commodity prices</p>
              </div>
            ) : pricesLoading ? (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-purple-600" />
                <p className="mt-2 text-gray-500">Loading prices...</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Crop</TableHead>
                    <TableHead className="text-right">Min Price</TableHead>
                    <TableHead className="text-right">Modal Price</TableHead>
                    <TableHead className="text-right">Max Price</TableHead>
                    <TableHead className="text-right">Change</TableHead>
                    <TableHead className="text-right">As Of</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {comparisonData.map((d) => (
                    <TableRow key={d.crop}>
                      <TableCell className="font-medium">{d.crop}</TableCell>
                      {d.noData ? (
                        <TableCell colSpan={5} className="text-center text-gray-400">
                          No price data available
                        </TableCell>
                      ) : (
                        <>
                          <TableCell className="text-right text-blue-600">₹{d.minPrice?.toFixed(2) || 'N/A'}/{d.unit}</TableCell>
                          <TableCell className="text-right font-semibold">₹{d.avgPrice?.toFixed(2) || 'N/A'}/{d.unit}</TableCell>
                          <TableCell className="text-right text-orange-600">₹{d.maxPrice?.toFixed(2) || 'N/A'}/{d.unit}</TableCell>
                          <TableCell className="text-right">
                            {d.priceChange !== null ? (
                              <span className={d.priceChange >= 0 ? "text-green-600" : "text-red-600"}>
                                {d.priceChange >= 0 ? <TrendingUp className="inline h-3 w-3 mr-1" /> : <TrendingDown className="inline h-3 w-3 mr-1" />}
                                {Math.abs(d.priceChange).toFixed(1)}%
                              </span>
                            ) : (
                              <span className="text-gray-400">N/A</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right text-sm text-gray-500">
                            {d.asOf ? new Date(d.asOf).toLocaleDateString() : 'N/A'}
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Main Page
export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState("price-trends");
  const { data: dashboardData, isLoading: dashboardLoading, refetch } = useQuery({ queryKey: ["analytics-dashboard"], queryFn: () => analyticsService.getDashboard(), staleTime: 5 * 60 * 1000, gcTime: 10 * 60 * 1000 });
  const { data: pricesData, isLoading: pricesLoading } = useQuery({ queryKey: ["prices-analytics"], queryFn: () => pricesService.getCurrentPrices(), staleTime: 5 * 60 * 1000, gcTime: 10 * 60 * 1000 });

  return (
    <AppLayout>
      <main className="flex-1 p-4 md:p-6 lg:p-8 overflow-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg"><BarChart3 className="h-6 w-6 text-green-600" /></div>
            <div><h1 className="text-2xl md:text-3xl font-bold">Market Research</h1><p className="text-muted-foreground text-sm">Analyze prices and commodities</p></div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => refetch()}><RefreshCw className="h-4 w-4 mr-2" />Refresh</Button>
          </div>
        </div>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2 lg:w-auto lg:inline-grid">
            <TabsTrigger value="price-trends"><TrendingUp className="h-4 w-4 mr-1" /><span className="hidden sm:inline">Price Trends</span></TabsTrigger>
            <TabsTrigger value="crop-comparison"><Scale className="h-4 w-4 mr-1" /><span className="hidden sm:inline">Compare</span></TabsTrigger>
          </TabsList>
          <TabsContent value="price-trends"><PriceTrendsTab dashboardData={dashboardData} pricesData={pricesData} isLoading={dashboardLoading || pricesLoading} /></TabsContent>
          <TabsContent value="crop-comparison"><CropComparisonTab /></TabsContent>
        </Tabs>
      </main>
    </AppLayout>
  );
}
