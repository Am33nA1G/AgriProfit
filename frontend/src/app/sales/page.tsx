'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesService, RecordSaleData, UpdateSaleData } from '@/services/sales';
import { inventoryService } from '@/services/inventory';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Sidebar } from "@/components/layout/Sidebar";
import { Navbar } from "@/components/layout/Navbar";
import { toast } from 'sonner';
import Link from 'next/link';
import {
    IndianRupee, TrendingUp, ShoppingCart, Trash2, Pencil,
    Search, ArrowUpDown, ArrowUp, ArrowDown, Download,
    Calculator, ShoppingBasket, Package, AlertTriangle
} from 'lucide-react';

type SortField = 'sale_date' | 'commodity_name' | 'quantity' | 'total_amount' | 'buyer_name';
type SortDir = 'asc' | 'desc';

function formatQuantity(quantity: number, unit: string): string {
    const display = `${quantity} ${unit}`;
    if (unit === 'kg' && quantity >= 100) {
        const qtl = (quantity / 100).toFixed(2).replace(/\.?0+$/, '');
        return `${display} (${qtl} qtl)`;
    }
    if (unit === 'kg' && quantity >= 1000) {
        const ton = (quantity / 1000).toFixed(2).replace(/\.?0+$/, '');
        return `${display} (${ton} ton)`;
    }
    return display;
}

function formatDate(dateStr: string): string {
    try {
        return new Date(dateStr).toLocaleDateString('en-IN', {
            day: '2-digit', month: 'short', year: 'numeric'
        });
    } catch {
        return dateStr;
    }
}

function SortIcon({ field, currentField, currentDir }: { field: SortField; currentField: SortField; currentDir: SortDir }) {
    if (field !== currentField) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-40" />;
    return currentDir === 'asc'
        ? <ArrowUp className="h-3 w-3 ml-1 text-green-600" />
        : <ArrowDown className="h-3 w-3 ml-1 text-green-600" />;
}

export default function SalesPage() {
    const t = useTranslations('sales');
    const tc = useTranslations('common');
    const queryClient = useQueryClient();

    // Dialog states
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<{
        id: string; quantity: number; unit: string; price_per_unit: number; buyer_name: string; sale_date: string;
        commodity_id: string; commodity_name: string;
    } | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

    // Search and sort
    const [searchQuery, setSearchQuery] = useState('');
    const [sortField, setSortField] = useState<SortField>('sale_date');
    const [sortDir, setSortDir] = useState<SortDir>('desc');

    // Form state
    const [formData, setFormData] = useState<RecordSaleData>({
        commodity_id: '',
        quantity: 0,
        unit: 'kg',
        price_per_unit: 0,
        buyer_name: '',
        sale_date: new Date().toISOString().split('T')[0]
    });

    // Queries
    const { data: sales, isLoading } = useQuery({
        queryKey: ['sales'],
        queryFn: salesService.getSalesHistory,
        staleTime: 2 * 60 * 1000,
        gcTime: 5 * 60 * 1000,
    });

    const { data: analytics } = useQuery({
        queryKey: ['sales-analytics'],
        queryFn: salesService.getAnalytics,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
    });

    // Fetch inventory stock instead of all commodities
    const { data: stock } = useQuery({
        queryKey: ['inventory-stock'],
        queryFn: inventoryService.getAvailableStock,
        staleTime: 1 * 60 * 1000,
        gcTime: 5 * 60 * 1000,
    });

    // Group stock by commodity for the dropdown (unique commodities with their units)
    const stockCommodities = useMemo(() => {
        if (!stock) return [];
        // Create unique commodity entries from stock
        const map = new Map<string, { id: string; name: string; stock: { unit: string; quantity: number }[] }>();
        for (const item of stock) {
            if (!map.has(item.commodity_id)) {
                map.set(item.commodity_id, {
                    id: item.commodity_id,
                    name: item.commodity_name || 'Unknown',
                    stock: []
                });
            }
            map.get(item.commodity_id)!.stock.push({ unit: item.unit, quantity: item.quantity });
        }
        return Array.from(map.values());
    }, [stock]);

    // Get available stock for current form selection
    const currentAvailableStock = useMemo(() => {
        if (!stock || !formData.commodity_id) return null;
        const match = stock.find(
            s => s.commodity_id === formData.commodity_id && s.unit === formData.unit
        );
        return match ? match.quantity : 0;
    }, [stock, formData.commodity_id, formData.unit]);

    // Get available stock for edit form
    const editAvailableStock = useMemo(() => {
        if (!stock || !editingItem) return null;
        const match = stock.find(
            s => s.commodity_id === editingItem.commodity_id && s.unit === editingItem.unit
        );
        // When editing, the old quantity is already deducted, so add it back
        const baseStock = match ? match.quantity : 0;
        // If same unit, the old sale quantity is "available" since we'll restore it
        return baseStock + editingItem.quantity;
    }, [stock, editingItem]);

    // Helper to invalidate all related queries
    const invalidateAll = () => {
        queryClient.invalidateQueries({ queryKey: ['sales'] });
        queryClient.invalidateQueries({ queryKey: ['sales-analytics'] });
        queryClient.invalidateQueries({ queryKey: ['inventory'] });
        queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
    };

    // Mutations
    const addMutation = useMutation({
        mutationFn: salesService.recordSale,
        onSuccess: () => {
            invalidateAll();
            setIsAddOpen(false);
            setFormData({ commodity_id: '', quantity: 0, unit: 'kg', price_per_unit: 0, buyer_name: '', sale_date: new Date().toISOString().split('T')[0] });
            toast.success('Sale recorded successfully');
        },
        onError: (err: any) => {
            const msg = err?.response?.data?.detail || 'Failed to record sale';
            toast.error(msg);
        }
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: UpdateSaleData }) => salesService.updateSale(id, data),
        onSuccess: () => {
            invalidateAll();
            setEditingItem(null);
            toast.success('Sale updated successfully');
        },
        onError: (err: any) => {
            const msg = err?.response?.data?.detail || 'Failed to update sale';
            toast.error(msg);
        }
    });

    const deleteMutation = useMutation({
        mutationFn: salesService.deleteSale,
        onSuccess: () => {
            invalidateAll();
            setDeleteTarget(null);
            toast.success('Sale deleted — stock restored to inventory');
        },
        onError: () => toast.error('Failed to delete sale')
    });

    // Filtered and sorted sales
    const filteredSales = useMemo(() => {
        if (!sales) return [];
        let result = [...sales];

        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            result = result.filter(s =>
                (s.commodity_name || '').toLowerCase().includes(q) ||
                (s.buyer_name || '').toLowerCase().includes(q)
            );
        }

        result.sort((a, b) => {
            let cmp = 0;
            switch (sortField) {
                case 'sale_date':
                    cmp = new Date(a.sale_date).getTime() - new Date(b.sale_date).getTime();
                    break;
                case 'commodity_name':
                    cmp = (a.commodity_name || '').localeCompare(b.commodity_name || '');
                    break;
                case 'quantity':
                    cmp = a.quantity - b.quantity;
                    break;
                case 'total_amount':
                    cmp = a.total_amount - b.total_amount;
                    break;
                case 'buyer_name':
                    cmp = (a.buyer_name || '').localeCompare(b.buyer_name || '');
                    break;
            }
            return sortDir === 'asc' ? cmp : -cmp;
        });

        return result;
    }, [sales, searchQuery, sortField, sortDir]);

    const avgSaleValue = analytics && analytics.total_sales_count > 0
        ? Math.round(analytics.total_revenue / analytics.total_sales_count)
        : 0;

    // Handlers
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.commodity_id || formData.quantity <= 0 || formData.price_per_unit <= 0) return;
        // Block if stock not loaded yet
        if (!stock) {
            toast.error('Loading inventory stock... please try again.');
            return;
        }
        // Always validate against available stock
        const available = currentAvailableStock ?? 0;
        if (formData.quantity > available) {
            toast.error(`Insufficient stock. Available: ${available} ${formData.unit}`);
            return;
        }
        addMutation.mutate(formData);
    };

    const handleEditSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingItem) return;
        updateMutation.mutate({
            id: editingItem.id,
            data: {
                quantity: editingItem.quantity,
                unit: editingItem.unit,
                price_per_unit: editingItem.price_per_unit,
                buyer_name: editingItem.buyer_name || undefined,
                sale_date: editingItem.sale_date,
            }
        });
    };

    const toggleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir(field === 'sale_date' || field === 'total_amount' ? 'desc' : 'asc');
        }
    };

    const exportCsv = () => {
        if (!sales || sales.length === 0) return;
        const headers = ['Date', 'Commodity', 'Quantity', 'Unit', 'Price/kg', 'Total', 'Buyer'];
        const rows = sales.map(s => [
            s.sale_date,
            s.commodity_name || '',
            s.quantity,
            s.unit,
            s.price_per_unit,
            s.total_amount,
            s.buyer_name || ''
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `sales_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(t('exportSuccess'));
    };

    // When commodity changes, auto-set unit to match available stock
    const handleCommodityChange = (commodityId: string) => {
        const commodity = stockCommodities.find(c => c.id === commodityId);
        const firstUnit = commodity?.stock[0]?.unit || 'kg';
        setFormData({ ...formData, commodity_id: commodityId, unit: firstUnit, quantity: 0 });
    };

    // Get available units for the selected commodity
    const availableUnitsForCommodity = useMemo(() => {
        if (!formData.commodity_id) return ['kg', 'quintal', 'ton'];
        const commodity = stockCommodities.find(c => c.id === formData.commodity_id);
        if (!commodity) return ['kg', 'quintal', 'ton'];
        return commodity.stock.map(s => s.unit);
    }, [formData.commodity_id, stockCommodities]);

    return (
        <div className="flex min-h-screen bg-gray-50 dark:bg-black">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Navbar />
                <main className="flex-1 p-6 md:p-8">
                    {/* Header */}
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
                        <div className="flex gap-2">
                            {sales && sales.length > 0 && (
                                <Button variant="outline" className="gap-2" onClick={exportCsv}>
                                    <Download className="h-4 w-4" /> {t('exportCsv')}
                                </Button>
                            )}
                            <Dialog open={isAddOpen} onOpenChange={(open) => {
                                setIsAddOpen(open);
                                if (open) {
                                    // Refresh stock when dialog opens
                                    queryClient.invalidateQueries({ queryKey: ['inventory-stock'] });
                                }
                            }}>
                                <DialogTrigger asChild>
                                    <Button className="gap-2 bg-green-600 hover:bg-green-700">
                                        <ShoppingCart className="h-4 w-4" /> {t('recordSale')}
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="sm:max-w-[425px]">
                                    <DialogHeader>
                                        <DialogTitle>{t('recordSale')}</DialogTitle>
                                    </DialogHeader>
                                    <form onSubmit={handleSubmit} className="space-y-4 pt-4">
                                        {/* Commodity — only from inventory */}
                                        <div className="space-y-2">
                                            <Label>{tc('commodity')}</Label>
                                            {stockCommodities.length === 0 ? (
                                                <div className="rounded-lg border border-orange-200 bg-orange-50 dark:bg-orange-950/30 dark:border-orange-800 p-3">
                                                    <div className="flex items-center gap-2 text-orange-700 dark:text-orange-400">
                                                        <Package className="h-4 w-4" />
                                                        <span className="text-sm font-medium">No inventory stock</span>
                                                    </div>
                                                    <p className="text-xs text-orange-600 dark:text-orange-500 mt-1">
                                                        Add commodities to your inventory first before recording a sale.
                                                    </p>
                                                    <Link href="/inventory">
                                                        <Button variant="outline" size="sm" className="mt-2 text-xs border-orange-300 text-orange-700 hover:bg-orange-100">
                                                            <Package className="h-3 w-3 mr-1" /> Go to Inventory
                                                        </Button>
                                                    </Link>
                                                </div>
                                            ) : (
                                                <Select
                                                    value={formData.commodity_id}
                                                    onValueChange={handleCommodityChange}
                                                >
                                                    <SelectTrigger>
                                                        <SelectValue placeholder={t('selectCommodity')} />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {stockCommodities.map((c) => (
                                                            <SelectItem key={c.id} value={c.id}>
                                                                {c.name} — {c.stock.map(s => `${s.quantity} ${s.unit}`).join(', ')}
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            )}
                                        </div>

                                        {stockCommodities.length > 0 && (
                                            <>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="space-y-2">
                                                        <Label>{tc('quantity')}</Label>
                                                        <Input
                                                            type="number"
                                                            min="0.01"
                                                            step="0.01"
                                                            max={currentAvailableStock ?? undefined}
                                                            value={formData.quantity || ''}
                                                            onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })}
                                                        />
                                                        {/* Show available stock */}
                                                        {formData.commodity_id && stock && (
                                                            <p className={`text-xs ${formData.quantity > (currentAvailableStock ?? 0) ? 'text-red-600 font-medium' : 'text-muted-foreground'}`}>
                                                                {formData.quantity > (currentAvailableStock ?? 0) ? (
                                                                    <span className="flex items-center gap-1">
                                                                        <AlertTriangle className="h-3 w-3" />
                                                                        Exceeds stock ({currentAvailableStock ?? 0} {formData.unit})
                                                                    </span>
                                                                ) : (
                                                                    `Available: ${currentAvailableStock ?? 0} ${formData.unit}`
                                                                )}
                                                            </p>
                                                        )}
                                                    </div>
                                                    <div className="space-y-2">
                                                        <Label>{tc('unit')}</Label>
                                                        <Select
                                                            value={formData.unit}
                                                            onValueChange={(v) => setFormData({ ...formData, unit: v, quantity: 0 })}
                                                        >
                                                            <SelectTrigger><SelectValue /></SelectTrigger>
                                                            <SelectContent>
                                                                {availableUnitsForCommodity.map(u => (
                                                                    <SelectItem key={u} value={u}>{u}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                </div>
                                                <div className="space-y-2">
                                                    <Label>{t('salePrice')} ({tc('rupees')}/{tc('kg')})</Label>
                                                    <Input
                                                        type="number"
                                                        min="0.01"
                                                        step="0.01"
                                                        value={formData.price_per_unit || ''}
                                                        onChange={(e) => setFormData({ ...formData, price_per_unit: parseFloat(e.target.value) || 0 })}
                                                    />
                                                    <p className="text-xs text-muted-foreground">
                                                        {t('unitConversion')}
                                                    </p>
                                                </div>
                                                <div className="space-y-2">
                                                    <Label>{t('saleDate')}</Label>
                                                    <Input
                                                        type="date"
                                                        value={formData.sale_date}
                                                        onChange={(e) => setFormData({ ...formData, sale_date: e.target.value })}
                                                    />
                                                </div>
                                                <div className="space-y-2">
                                                    <Label>{t('buyerName')}</Label>
                                                    <Input
                                                        value={formData.buyer_name}
                                                        onChange={(e) => setFormData({ ...formData, buyer_name: e.target.value })}
                                                        placeholder="e.g. Local Mandi"
                                                    />
                                                </div>

                                                {/* Estimated total preview */}
                                                {formData.quantity > 0 && formData.price_per_unit > 0 && (
                                                    <div className="rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 p-3">
                                                        <p className="text-xs text-green-700 dark:text-green-400 mb-1">Estimated Total</p>
                                                        <p className="text-lg font-bold text-green-700 dark:text-green-400">
                                                            ₹{(() => {
                                                                let qtyKg = formData.quantity;
                                                                if (formData.unit === 'quintal') qtyKg *= 100;
                                                                if (formData.unit === 'ton') qtyKg *= 1000;
                                                                return (qtyKg * formData.price_per_unit).toLocaleString();
                                                            })()}
                                                        </p>
                                                    </div>
                                                )}

                                                <Button
                                                    type="submit"
                                                    className="w-full bg-green-600"
                                                    disabled={
                                                        addMutation.isPending ||
                                                        !formData.commodity_id ||
                                                        formData.quantity <= 0 ||
                                                        formData.price_per_unit <= 0 ||
                                                        !stock ||
                                                        formData.quantity > (currentAvailableStock ?? 0)
                                                    }
                                                >
                                                    {addMutation.isPending ? tc('saving') : t('recordSale')}
                                                </Button>
                                            </>
                                        )}
                                    </form>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </div>

                    {/* Stats Cards - 4 cards */}
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">{t('totalRevenue')}</CardTitle>
                                <IndianRupee className="h-4 w-4 text-green-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">₹{analytics?.total_revenue?.toLocaleString() || '0'}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">{t('title')}</CardTitle>
                                <ShoppingCart className="h-4 w-4 text-blue-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{analytics?.total_sales_count || 0}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">{t('avgSaleValue')}</CardTitle>
                                <Calculator className="h-4 w-4 text-orange-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">₹{avgSaleValue.toLocaleString()}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">{tc('trending')}</CardTitle>
                                <TrendingUp className="h-4 w-4 text-purple-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold truncate">{analytics?.top_selling_commodity || '-'}</div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* Sales Table */}
                    <Card>
                        <CardHeader>
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                                <div>
                                    <CardTitle>{t('subtitle')}</CardTitle>
                                    <CardDescription>{t('analytics')}</CardDescription>
                                </div>
                                <div className="relative w-full sm:w-72">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        placeholder={t('searchSales')}
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-9"
                                    />
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort('sale_date')}>
                                                <span className="flex items-center">{tc('date')}<SortIcon field="sale_date" currentField={sortField} currentDir={sortDir} /></span>
                                            </TableHead>
                                            <TableHead className="cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort('commodity_name')}>
                                                <span className="flex items-center">{tc('commodity')}<SortIcon field="commodity_name" currentField={sortField} currentDir={sortDir} /></span>
                                            </TableHead>
                                            <TableHead className="cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort('quantity')}>
                                                <span className="flex items-center">{tc('quantity')}<SortIcon field="quantity" currentField={sortField} currentDir={sortDir} /></span>
                                            </TableHead>
                                            <TableHead>{tc('price')}/{tc('kg')}</TableHead>
                                            <TableHead className="cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort('total_amount')}>
                                                <span className="flex items-center">{tc('total')}<SortIcon field="total_amount" currentField={sortField} currentDir={sortDir} /></span>
                                            </TableHead>
                                            <TableHead className="cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort('buyer_name')}>
                                                <span className="flex items-center">{t('buyerName')}<SortIcon field="buyer_name" currentField={sortField} currentDir={sortDir} /></span>
                                            </TableHead>
                                            <TableHead className="text-right">{tc('actions')}</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {isLoading ? (
                                            <TableRow><TableCell colSpan={7} className="text-center">{tc('loading')}</TableCell></TableRow>
                                        ) : !sales || sales.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={7} className="h-48">
                                                    <div className="flex flex-col items-center justify-center text-center py-8">
                                                        <ShoppingBasket className="h-12 w-12 text-muted-foreground/40 mb-4" />
                                                        <h3 className="text-lg font-semibold mb-1">{t('noSales')}</h3>
                                                        <p className="text-sm text-muted-foreground mb-4 max-w-xs">
                                                            {t('noSalesDesc')}
                                                        </p>
                                                        <div className="flex gap-2">
                                                            <Link href="/inventory">
                                                                <Button variant="outline" className="gap-2">
                                                                    <Package className="h-4 w-4" /> Add Inventory
                                                                </Button>
                                                            </Link>
                                                            <Button
                                                                className="gap-2 bg-green-600 hover:bg-green-700"
                                                                onClick={() => setIsAddOpen(true)}
                                                            >
                                                                <ShoppingCart className="h-4 w-4" /> {t('recordSale')}
                                                            </Button>
                                                        </div>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ) : filteredSales.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                                                    {t('noMatchingSales')}
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            filteredSales.map((sale) => (
                                                <TableRow key={sale.id}>
                                                    <TableCell>{formatDate(sale.sale_date)}</TableCell>
                                                    <TableCell className="font-medium">{sale.commodity_name || tc('loading')}</TableCell>
                                                    <TableCell>{formatQuantity(sale.quantity, sale.unit)}</TableCell>
                                                    <TableCell>₹{sale.price_per_unit.toLocaleString()}</TableCell>
                                                    <TableCell className="text-green-600 font-bold">₹{sale.total_amount.toLocaleString()}</TableCell>
                                                    <TableCell>{sale.buyer_name || '-'}</TableCell>
                                                    <TableCell className="text-right">
                                                        <div className="flex justify-end gap-1">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="text-blue-500 hover:text-blue-600 hover:bg-blue-50"
                                                                onClick={() => setEditingItem({
                                                                    id: sale.id,
                                                                    quantity: sale.quantity,
                                                                    unit: sale.unit,
                                                                    price_per_unit: sale.price_per_unit,
                                                                    buyer_name: sale.buyer_name || '',
                                                                    sale_date: sale.sale_date,
                                                                    commodity_id: sale.commodity_id,
                                                                    commodity_name: sale.commodity_name || 'Unknown',
                                                                })}
                                                            >
                                                                <Pencil className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                                                onClick={() => setDeleteTarget({
                                                                    id: sale.id,
                                                                    name: `${sale.commodity_name || 'Sale'} - ₹${sale.total_amount.toLocaleString()}`
                                                                })}
                                                                disabled={deleteMutation.isPending}
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Edit Sale Dialog */}
                    <Dialog open={!!editingItem} onOpenChange={(open) => !open && setEditingItem(null)}>
                        <DialogContent className="sm:max-w-[425px]">
                            <DialogHeader>
                                <DialogTitle>{t('editSale')} — {editingItem?.commodity_name}</DialogTitle>
                            </DialogHeader>
                            {editingItem && (
                                <form onSubmit={handleEditSubmit} className="space-y-4 pt-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label>{tc('quantity')}</Label>
                                            <Input
                                                type="number"
                                                min="0.01"
                                                step="0.01"
                                                value={editingItem.quantity}
                                                onChange={(e) => setEditingItem({ ...editingItem, quantity: parseFloat(e.target.value) || 0 })}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>{tc('unit')}</Label>
                                            <Select
                                                value={editingItem.unit}
                                                onValueChange={(v) => setEditingItem({ ...editingItem, unit: v })}
                                            >
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
                                        <Label>{t('salePrice')} ({tc('rupees')}/{tc('kg')})</Label>
                                        <Input
                                            type="number"
                                            min="0.01"
                                            step="0.01"
                                            value={editingItem.price_per_unit}
                                            onChange={(e) => setEditingItem({ ...editingItem, price_per_unit: parseFloat(e.target.value) || 0 })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('saleDate')}</Label>
                                        <Input
                                            type="date"
                                            value={editingItem.sale_date}
                                            onChange={(e) => setEditingItem({ ...editingItem, sale_date: e.target.value })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label>{t('buyerName')}</Label>
                                        <Input
                                            value={editingItem.buyer_name}
                                            onChange={(e) => setEditingItem({ ...editingItem, buyer_name: e.target.value })}
                                            placeholder="e.g. Local Mandi"
                                        />
                                    </div>
                                    <Button type="submit" className="w-full bg-green-600" disabled={updateMutation.isPending}>
                                        {updateMutation.isPending ? tc('saving') : tc('saveChanges')}
                                    </Button>
                                </form>
                            )}
                        </DialogContent>
                    </Dialog>

                    {/* Delete Confirmation Dialog */}
                    <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
                        <DialogContent className="sm:max-w-[400px]">
                            <DialogHeader>
                                <DialogTitle>{t('deleteConfirm')}</DialogTitle>
                            </DialogHeader>
                            <div className="py-4">
                                <p className="text-sm text-muted-foreground">
                                    <span className="font-medium text-foreground">{deleteTarget?.name}</span>
                                </p>
                                <p className="text-sm text-green-600 mt-2">
                                    The sold quantity will be restored back to your inventory.
                                </p>
                            </div>
                            <div className="flex justify-end gap-2">
                                <Button variant="outline" onClick={() => setDeleteTarget(null)}>{tc('cancel')}</Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
                                    disabled={deleteMutation.isPending}
                                >
                                    {deleteMutation.isPending ? tc('deleting') : tc('delete')}
                                </Button>
                            </div>
                        </DialogContent>
                    </Dialog>
                </main>
            </div>
        </div>
    );
}
