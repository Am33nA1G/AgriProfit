'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryService, AddInventoryData } from '@/services/inventory';
import { commoditiesService } from '@/services/commodities';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Sidebar } from "@/components/layout/Sidebar";
import { Navbar } from "@/components/layout/Navbar";
import { toast } from 'sonner';
import { Plus, Trash2, Package, BarChart3 } from 'lucide-react';
import Link from 'next/link';

export default function InventoryPage() {
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
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

    const deleteMutation = useMutation({
        mutationFn: inventoryService.deleteInventory,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['inventory'] });
            toast.success('Item removed');
            setDeleteTarget(null);
        }
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.commodity_id || formData.quantity <= 0) return;
        addMutation.mutate(formData);
    };

    return (
        <div className="flex min-h-screen bg-gray-50 dark:bg-black">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Navbar />
                <main className="flex-1 p-6 md:p-8">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold tracking-tight">My Inventory</h1>
                        <div className="flex gap-2">
                            <Button variant="outline" className="gap-2" asChild>
                                <Link href="/dashboard/analyze">
                                    <BarChart3 className="h-4 w-4" /> Analyze Inventory
                                </Link>
                            </Button>
                            <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                                <DialogTrigger asChild>
                                    <Button className="gap-2">
                                        <Plus className="h-4 w-4" /> Add Stock
                                    </Button>
                                </DialogTrigger>
                            <DialogContent className="sm:max-w-[425px]">
                                <DialogHeader>
                                    <DialogTitle>Add Inventory</DialogTitle>
                                </DialogHeader>
                                <form onSubmit={handleSubmit} className="space-y-4 pt-4">
                                    <div className="space-y-2">
                                        <Label>Commodity</Label>
                                        <Select
                                            value={formData.commodity_id}
                                            onValueChange={(v) => setFormData({ ...formData, commodity_id: v })}
                                        >
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select commodity" />
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
                                            <Label>Quantity</Label>
                                            <Input
                                                type="number"
                                                min="0.01"
                                                step="0.01"
                                                value={formData.quantity || ''}
                                                onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) })}
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <Label>Unit</Label>
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
                                        {addMutation.isPending ? 'Adding...' : 'Save Stock'}
                                    </Button>
                                </form>
                            </DialogContent>
                            </Dialog>
                        </div>
                    </div>

                    {isLoading ? (
                        <div>Loading inventory...</div>
                    ) : inventory?.length === 0 ? (
                        <div className="text-center py-12 bg-white rounded-lg border border-dashed">
                            <Package className="mx-auto h-12 w-12 text-gray-400" />
                            <h3 className="mt-2 text-sm font-semibold text-gray-900">No inventory</h3>
                            <p className="mt-1 text-sm text-gray-500">Get started by adding your produce stock.</p>
                        </div>
                    ) : (
                        <div className="grid gap-6">
                            <Card>
                                <CardContent className="p-0">
                                    <div className="overflow-x-auto">
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>Commodity</TableHead>
                                                    <TableHead>Quantity</TableHead>
                                                    <TableHead>Unit</TableHead>
                                                    <TableHead className="text-right">Actions</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {inventory?.map((item) => (
                                                    <TableRow key={item.id}>
                                                        <TableCell className="font-medium">{item.commodity_name || 'Loading...'}</TableCell>
                                                        <TableCell>{item.quantity}</TableCell>
                                                        <TableCell>{item.unit}</TableCell>
                                                        <TableCell className="text-right">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                                                onClick={() => setDeleteTarget({ id: item.id, name: item.commodity_name || 'this item' })}
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </main>
            </div>

            {/* Delete Confirmation Dialog */}
            <Dialog open={!!deleteTarget} onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}>
                <DialogContent className="sm:max-w-[380px]">
                    <DialogHeader>
                        <DialogTitle>Remove Item</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to remove <span className="font-semibold">{deleteTarget?.name}</span> from your inventory? This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="gap-2 sm:gap-0">
                        <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleteMutation.isPending}>
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
                            disabled={deleteMutation.isPending}
                        >
                            {deleteMutation.isPending ? 'Removing...' : 'Remove'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
