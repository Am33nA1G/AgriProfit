'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryService, AddInventoryData, UpdateInventoryData } from '@/services/inventory';
import { commoditiesService } from '@/services/commodities';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Sidebar } from "@/components/layout/Sidebar";
import { Navbar } from "@/components/layout/Navbar";
import { toast } from 'sonner';
import { Plus, Trash2, Package, BarChart3, Pencil, Search, ArrowUpDown, ArrowUp, ArrowDown, ShoppingBasket, Calendar, Layers } from 'lucide-react';
import Link from 'next/link';

type SortField = 'commodity_name' | 'quantity' | 'unit' | 'created_at';
type SortDir = 'asc' | 'desc';

export default function InventoryPage() {
    const t = useTranslations('inventory');
    const tc = useTranslations('common');
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [editingItem, setEditingItem] = useState<{ id: string; quantity: number; unit: string } | null>(null);
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [sortField, setSortField] = useState<SortField>('created_at');
    const [sortDir, setSortDir] = useState<SortDir>('desc');
    const [formData, setFormData] = useState<AddInventoryData>({
        commodity_id: '',
        quantity: 0,
        unit: 'kg'
    });

    const { data: inventory, isLoading } = useQuery({
        queryKey: ['inventory'],
        queryFn: inventoryService.getInventory,
        staleTime: 2 * 60 * 1000,
        gcTime: 5 * 60 * 1000,
    });

    const { data: commodities } = useQuery({
        queryKey: ['commodities'],
        queryFn: () => commoditiesService.getAll({ limit: 500 }),
        staleTime: 10 * 60 * 1000,
        gcTime: 15 * 60 * 1000,
    });

    const addMutation = useMutation({
        mutationFn: inventoryService.addInventory,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            setIsAddOpen(false);
            toast.success('Inventory added successfully');
            setFormData({ commodity_id: '', quantity: 0, unit: 'kg' });
        },
        onError: () => toast.error('Failed to add inventory')
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: UpdateInventoryData }) =>
            inventoryService.updateInventory(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            setEditingItem(null);
            toast.success('Quantity updated');
        },
        onError: () => toast.error('Failed to update inventory')
    });

    const deleteMutation = useMutation({
        mutationFn: inventoryService.deleteInventory,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            setDeleteTarget(null);
            toast.success('Item removed');
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.commodity_id || formData.quantity <= 0) return;
        addMutation.mutate(formData);
    };

    const handleEditSubmit = () => {
        if (!editingItem || editingItem.quantity <= 0) return;
        updateMutation.mutate({
            id: editingItem.id,
            data: { quantity: editingItem.quantity, unit: editingItem.unit }
        });
    };

    // --- Search + Sort ---
    const filteredAndSorted = useMemo(() => {
        if (!inventory) return [];
        let items = [...inventory];

        // Filter by search query
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            items = items.filter(item =>
                (item.commodity_name || '').toLowerCase().includes(q)
            );
        }

        // Sort
        items.sort((a, b) => {
            let cmp = 0;
            switch (sortField) {
                case 'commodity_name':
                    cmp = (a.commodity_name || '').localeCompare(b.commodity_name || '');
                    break;
                case 'quantity':
                    cmp = a.quantity - b.quantity;
                    break;
                case 'unit':
                    cmp = a.unit.localeCompare(b.unit);
                    break;
                case 'created_at':
                    cmp = new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime();
                    break;
            }
            return sortDir === 'asc' ? cmp : -cmp;
        });

        return items;
    }, [inventory, searchQuery, sortField, sortDir]);

    // --- Stats ---
    const stats = useMemo(() => {
        if (!inventory || inventory.length === 0) return null;
        const uniqueCommodities = new Set(inventory.map(i => i.commodity_id)).size;
        const lastUpdated = inventory.reduce((latest, item) => {
            const d = new Date(item.updated_at || item.created_at || 0);
            return d > latest ? d : latest;
        }, new Date(0));
        return {
            totalItems: inventory.length,
            uniqueCommodities,
            lastUpdated,
        };
    }, [inventory]);

    const toggleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDir(field === 'created_at' ? 'desc' : 'asc');
        }
    };

    const SortIcon = ({ field }: { field: SortField }) => {
        if (sortField !== field) return <ArrowUpDown className="h-3 w-3 ml-1 opacity-40" />;
        return sortDir === 'asc'
            ? <ArrowUp className="h-3 w-3 ml-1 text-primary" />
            : <ArrowDown className="h-3 w-3 ml-1 text-primary" />;
    };

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '-';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    };

    const formatQuantity = (qty: number, unit: string) => {
        if (unit === 'kg' && qty >= 100) {
            const quintals = qty / 100;
            if (Number.isInteger(quintals)) return `${qty.toLocaleString('en-IN')} kg (${quintals} qtl)`;
            return `${qty.toLocaleString('en-IN')} kg (${quintals.toFixed(1)} qtl)`;
        }
        if (unit === 'kg' && qty >= 1000) {
            return `${qty.toLocaleString('en-IN')} kg (${(qty / 1000).toFixed(1)} ton)`;
        }
        return `${qty.toLocaleString('en-IN')}`;
    };

    return (
        <div className="flex min-h-screen bg-gray-50 dark:bg-black">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Navbar />
                <main className="flex-1 p-6 md:p-8">
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
                            <p className="text-sm text-muted-foreground mt-1">{t('subtitle')}</p>
                        </div>
                        <div className="flex items-center gap-3">
                            {inventory && inventory.length > 0 && (
                                <Link href="/dashboard/analyze">
                                    <Button className="gap-2 bg-green-600 text-white hover:bg-green-700">
                                        <BarChart3 className="h-4 w-4" /> {t('analyze')}
                                    </Button>
                                </Link>
                            )}
                            <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                                <DialogTrigger asChild>
                                    <Button className="gap-2">
                                        <Plus className="h-4 w-4" /> {t('addItem')}
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="sm:max-w-[425px]">
                                    <DialogHeader>
                                        <DialogTitle>{t('addInventory')}</DialogTitle>
                                        <DialogDescription>
                                            Add a commodity to your inventory. If it already exists, the quantity will be added.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <form onSubmit={handleSubmit} className="space-y-4 pt-4">
                                        <div className="space-y-2">
                                            <Label>{tc('commodity')}</Label>
                                            <Select
                                                value={formData.commodity_id}
                                                onValueChange={(v) => setFormData({ ...formData, commodity_id: v })}
                                            >
                                                <SelectTrigger>
                                                    <SelectValue placeholder={t('selectCommodity')} />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {commodities?.map((c: any) => (
                                                        <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="space-y-2">
                                                <Label>{t('quantity')}</Label>
                                                <Input
                                                    type="number"
                                                    min="0.01"
                                                    step="0.01"
                                                    value={formData.quantity || ''}
                                                    onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                            <div className="space-y-2">
                                                <Label>{tc('unit')}</Label>
                                                <Select
                                                    value={formData.unit}
                                                    onValueChange={(v) => setFormData({ ...formData, unit: v })}
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
                                        <Button type="submit" className="w-full" disabled={addMutation.isPending}>
                                            {addMutation.isPending ? tc('saving') : tc('save')}
                                        </Button>
                                    </form>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </div>

                    {/* Stats Bar */}
                    {stats && (
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                            <Card>
                                <CardContent className="flex items-center gap-3 p-4">
                                    <div className="rounded-lg bg-blue-100 dark:bg-blue-900/30 p-2.5">
                                        <Package className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{tc('total')} Items</p>
                                        <p className="text-2xl font-bold">{stats.totalItems}</p>
                                    </div>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="flex items-center gap-3 p-4">
                                    <div className="rounded-lg bg-green-100 dark:bg-green-900/30 p-2.5">
                                        <Layers className="h-5 w-5 text-green-600 dark:text-green-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">{tc('commodities')}</p>
                                        <p className="text-2xl font-bold">{stats.uniqueCommodities}</p>
                                    </div>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="flex items-center gap-3 p-4">
                                    <div className="rounded-lg bg-orange-100 dark:bg-orange-900/30 p-2.5">
                                        <Calendar className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                                    </div>
                                    <div>
                                        <p className="text-sm text-muted-foreground">Last Updated</p>
                                        <p className="text-lg font-bold">{formatDate(stats.lastUpdated.toISOString())}</p>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    )}

                    {isLoading ? (
                        <div className="flex items-center justify-center py-16">
                            <div className="text-center">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-3"></div>
                                <p className="text-muted-foreground">{tc('loading')}</p>
                            </div>
                        </div>
                    ) : !inventory || inventory.length === 0 ? (
                        /* Enhanced Empty State */
                        <div className="text-center py-16 bg-white dark:bg-gray-900 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700">
                            <ShoppingBasket className="mx-auto h-16 w-16 text-gray-300 dark:text-gray-600 mb-4" />
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{t('noItems')}</h3>
                            <p className="mt-1 text-sm text-muted-foreground max-w-sm mx-auto">
                                {t('noItemsDesc')}. Track your crops to get mandi recommendations and revenue estimates.
                            </p>
                            <div className="flex items-center justify-center gap-3 mt-6">
                                <Button className="gap-2" onClick={() => setIsAddOpen(true)}>
                                    <Plus className="h-4 w-4" /> {t('addItem')}
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid gap-4">
                            {/* Search Bar */}
                            <div className="relative max-w-sm">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search by commodity name..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10"
                                />
                            </div>

                            {/* Table */}
                            <Card>
                                <CardContent className="p-0">
                                    <div className="overflow-x-auto">
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>
                                                        <button onClick={() => toggleSort('commodity_name')} className="flex items-center hover:text-foreground transition-colors font-medium">
                                                            {tc('commodity')}<SortIcon field="commodity_name" />
                                                        </button>
                                                    </TableHead>
                                                    <TableHead>
                                                        <button onClick={() => toggleSort('quantity')} className="flex items-center hover:text-foreground transition-colors font-medium">
                                                            {t('quantity')}<SortIcon field="quantity" />
                                                        </button>
                                                    </TableHead>
                                                    <TableHead>
                                                        <button onClick={() => toggleSort('unit')} className="flex items-center hover:text-foreground transition-colors font-medium">
                                                            {tc('unit')}<SortIcon field="unit" />
                                                        </button>
                                                    </TableHead>
                                                    <TableHead>
                                                        <button onClick={() => toggleSort('created_at')} className="flex items-center hover:text-foreground transition-colors font-medium">
                                                            {t('addedOn')}<SortIcon field="created_at" />
                                                        </button>
                                                    </TableHead>
                                                    <TableHead className="text-right">{tc('actions')}</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {filteredAndSorted.length === 0 ? (
                                                    <TableRow>
                                                        <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                                                            No items match &quot;{searchQuery}&quot;
                                                        </TableCell>
                                                    </TableRow>
                                                ) : (
                                                    filteredAndSorted.map((item) => (
                                                        <TableRow key={item.id}>
                                                            <TableCell className="font-medium">{item.commodity_name || tc('loading')}</TableCell>
                                                            <TableCell>
                                                                <span>{formatQuantity(item.quantity, item.unit)}</span>
                                                            </TableCell>
                                                            <TableCell>
                                                                <Badge variant="outline" className="font-normal">{item.unit}</Badge>
                                                            </TableCell>
                                                            <TableCell className="text-muted-foreground text-sm">
                                                                {formatDate(item.created_at)}
                                                            </TableCell>
                                                            <TableCell className="text-right">
                                                                <div className="flex items-center justify-end gap-1">
                                                                    <Button
                                                                        variant="ghost"
                                                                        size="icon"
                                                                        className="text-blue-500 hover:text-blue-600 hover:bg-blue-50"
                                                                        onClick={() => setEditingItem({ id: item.id, quantity: item.quantity, unit: item.unit })}
                                                                    >
                                                                        <Pencil className="h-4 w-4" />
                                                                    </Button>
                                                                    <Button
                                                                        variant="ghost"
                                                                        size="icon"
                                                                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                                                        onClick={() => setDeleteTarget({ id: item.id, name: item.commodity_name || 'this item' })}
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

                            {/* Result count */}
                            {searchQuery && (
                                <p className="text-xs text-muted-foreground">
                                    Showing {filteredAndSorted.length} of {inventory.length} items
                                </p>
                            )}
                        </div>
                    )}

                    {/* Edit Dialog */}
                    <Dialog open={!!editingItem} onOpenChange={(open) => !open && setEditingItem(null)}>
                        <DialogContent className="sm:max-w-[360px]">
                            <DialogHeader>
                                <DialogTitle>{t('editItem')}</DialogTitle>
                                <DialogDescription>Update the quantity or unit for this item.</DialogDescription>
                            </DialogHeader>
                            {editingItem && (
                                <div className="space-y-4 pt-2">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <Label>{t('quantity')}</Label>
                                            <Input
                                                type="number"
                                                min="0.01"
                                                step="0.01"
                                                value={editingItem.quantity || ''}
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
                                    <DialogFooter>
                                        <Button variant="outline" onClick={() => setEditingItem(null)}>
                                            {tc('cancel')}
                                        </Button>
                                        <Button onClick={handleEditSubmit} disabled={updateMutation.isPending}>
                                            {updateMutation.isPending ? tc('saving') : tc('save')}
                                        </Button>
                                    </DialogFooter>
                                </div>
                            )}
                        </DialogContent>
                    </Dialog>

                    {/* Delete Confirmation Dialog */}
                    <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
                        <DialogContent className="sm:max-w-[400px]">
                            <DialogHeader>
                                <DialogTitle className="text-red-600">Remove Item</DialogTitle>
                                <DialogDescription>
                                    Are you sure you want to remove <strong>{deleteTarget?.name}</strong> from your inventory? This cannot be undone.
                                </DialogDescription>
                            </DialogHeader>
                            <DialogFooter className="gap-2 sm:gap-0">
                                <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                                    {tc('cancel')}
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
                                    disabled={deleteMutation.isPending}
                                >
                                    {deleteMutation.isPending ? 'Removing...' : tc('delete')}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </main>
            </div>
        </div>
    );
}
