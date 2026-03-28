'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { salesService, RecordSaleData } from '@/services/sales';
import { commoditiesService } from '@/services/commodities';
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
import { IndianRupee, TrendingUp, ShoppingCart, Trash2, Download, FileText } from 'lucide-react';
import { Checkbox } from "@/components/ui/checkbox";
import type { SaleItem } from '@/services/sales';

function downloadInvoice(items: SaleItem[], title: string) {
    const total = items.reduce((sum, s) => sum + s.total_amount, 0);
    const rows = items.map((s) => `
        <tr>
            <td>${new Date(s.sale_date).toLocaleDateString('en-IN')}</td>
            <td>${s.commodity_name || s.commodity_id}</td>
            <td>${s.quantity} ${s.unit}</td>
            <td>₹${s.price_per_unit.toLocaleString('en-IN')}</td>
            <td>${s.buyer_name || '—'}</td>
            <td class="amount">₹${s.total_amount.toLocaleString('en-IN')}</td>
        </tr>`).join('');

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>${title}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #111; padding: 40px; }
  .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
  .brand { font-size: 24px; font-weight: 700; color: #16a34a; }
  .brand small { display: block; font-size: 13px; font-weight: 400; color: #555; margin-top: 2px; }
  .meta { text-align: right; font-size: 13px; color: #555; }
  .meta strong { font-size: 18px; color: #111; display: block; margin-bottom: 4px; }
  h2 { font-size: 15px; font-weight: 600; margin-bottom: 12px; color: #333; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px; }
  thead tr { background: #f0fdf4; }
  th { padding: 10px 12px; text-align: left; font-weight: 600; color: #166534; border-bottom: 2px solid #bbf7d0; }
  td { padding: 9px 12px; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .amount { font-weight: 600; text-align: right; }
  th:last-child { text-align: right; }
  .totals { display: flex; justify-content: flex-end; }
  .totals table { width: auto; min-width: 260px; }
  .totals td { padding: 6px 12px; border: none; }
  .totals .grand-total td { font-size: 16px; font-weight: 700; color: #16a34a; border-top: 2px solid #bbf7d0; padding-top: 10px; }
  .footer { margin-top: 40px; font-size: 11px; color: #9ca3af; text-align: center; border-top: 1px solid #e5e7eb; padding-top: 16px; }
  @media print { body { padding: 20px; } }
</style>
</head>
<body>
  <div class="header">
    <div class="brand">AgriProfit<small>Farm Management Platform</small></div>
    <div class="meta"><strong>${title}</strong>Generated: ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
  </div>
  <h2>Sale Transactions</h2>
  <table>
    <thead><tr><th>Date</th><th>Commodity</th><th>Qty &amp; Unit</th><th>Price / Unit</th><th>Buyer</th><th>Amount</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
  <div class="totals">
    <table>
      <tr><td>Subtotal (${items.length} sale${items.length !== 1 ? 's' : ''})</td><td class="amount">₹${total.toLocaleString('en-IN')}</td></tr>
      <tr class="grand-total"><td><strong>Total Revenue</strong></td><td class="amount"><strong>₹${total.toLocaleString('en-IN')}</strong></td></tr>
    </table>
  </div>
  <div class="footer">This is a system-generated document from AgriProfit · ${new Date().toISOString()}</div>
</body>
</html>`;

    const win = window.open('', '_blank', 'width=900,height=700');
    if (!win) { return; }
    win.document.write(html);
    win.document.close();
    win.focus();
    win.print();
}

export default function SalesPage() {
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    const toggleSelect = (id: string) =>
        setSelectedIds((prev) => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });

    const toggleSelectAll = (allIds: string[]) =>
        setSelectedIds((prev) =>
            prev.size === allIds.length ? new Set() : new Set(allIds)
        );
    const [formData, setFormData] = useState<RecordSaleData>({
        commodity_id: '',
        quantity: 0,
        unit: 'kg',
        price_per_unit: 0,
        buyer_name: '',
        sale_date: new Date().toISOString().split('T')[0]
    });

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

    const { data: commodities } = useQuery({
        queryKey: ['commodities'],
        queryFn: () => commoditiesService.getAll({ limit: 500 }),
        staleTime: 10 * 60 * 1000,
        gcTime: 15 * 60 * 1000,
    });

    const addMutation = useMutation({
        mutationFn: salesService.recordSale,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['sales'] });
            queryClient.invalidateQueries({ queryKey: ['sales-analytics'] });
            queryClient.invalidateQueries({ queryKey: ['inventory'] }); // Update inventory too
            setIsAddOpen(false);
            toast.success('Sale recorded successfully');
        },
        onError: () => toast.error('Failed to record sale')
    });

    const deleteMutation = useMutation({
        mutationFn: salesService.deleteSale,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['sales'] });
            queryClient.invalidateQueries({ queryKey: ['sales-analytics'] });
            toast.success('Sale deleted');
        },
        onError: () => toast.error('Failed to delete sale')
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.commodity_id || formData.quantity <= 0 || formData.price_per_unit <= 0) return;
        addMutation.mutate(formData);
    };

    return (
        <div className="flex min-h-screen bg-gray-50 dark:bg-black">
            <Sidebar />
            <div className="flex-1 flex flex-col">
                <Navbar />
                <main className="flex-1 p-6 md:p-8">
                    <div className="flex justify-between items-center mb-6">
                        <h1 className="text-3xl font-bold tracking-tight">Sales & Revenue</h1>
                        <div className="flex items-center gap-2">
                            {selectedIds.size > 0 ? (
                                <Button
                                    variant="outline"
                                    className="gap-2"
                                    onClick={() => {
                                        const selected = (sales ?? []).filter((s) => selectedIds.has(s.id));
                                        downloadInvoice(selected, `Sales Invoice — ${selectedIds.size} selected sale${selectedIds.size !== 1 ? 's' : ''}`);
                                    }}
                                >
                                    <Download className="h-4 w-4 text-blue-600" />
                                    <span className="hidden sm:inline">Download Selected ({selectedIds.size})</span>
                                </Button>
                            ) : (
                                <Button
                                    variant="outline"
                                    className="gap-2"
                                    onClick={() => sales && sales.length > 0 ? downloadInvoice(sales, 'Sales Invoice — All Transactions') : toast.info('No sales to download')}
                                >
                                    <FileText className="h-4 w-4 text-blue-600" />
                                    <span className="hidden sm:inline">Download All</span>
                                </Button>
                            )}
                        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                            <DialogTrigger asChild>
                                <Button className="gap-2 bg-green-600 hover:bg-green-700">
                                    <ShoppingCart className="h-4 w-4" /> Record Sale
                                </Button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[425px]">
                                <DialogHeader>
                                    <DialogTitle>Record New Sale</DialogTitle>
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
                                    <div className="space-y-2">
                                        <Label>Price per kg (₹)</Label>
                                        <Input
                                            type="number"
                                            min="0.01"
                                            step="0.01"
                                            value={formData.price_per_unit || ''}
                                            onChange={(e) => setFormData({ ...formData, price_per_unit: parseFloat(e.target.value) })}
                                        />
                                        <p className="text-xs text-muted-foreground">
                                            Totals are calculated in kg (1 quintal = 100 kg, 1 ton = 1000 kg).
                                        </p>
                                    </div>
                                    <div className="space-y-2">
                                        <Label>Buyer Name (Optional)</Label>
                                        <Input
                                            value={formData.buyer_name}
                                            onChange={(e) => setFormData({ ...formData, buyer_name: e.target.value })}
                                            placeholder="e.g. Local Mandi"
                                        />
                                    </div>
                                    <Button type="submit" className="w-full bg-green-600" disabled={addMutation.isPending}>
                                        {addMutation.isPending ? 'Recording...' : 'Confirm Sale'}
                                    </Button>
                                </form>
                            </DialogContent>
                        </Dialog>
                        </div>
                    </div>

                    {/* Stats Cards */}
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                                <IndianRupee className="h-4 w-4 text-green-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">₹{analytics?.total_revenue?.toLocaleString() || '0'}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Sales</CardTitle>
                                <ShoppingCart className="h-4 w-4 text-blue-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{analytics?.total_sales_count || 0}</div>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Top Product</CardTitle>
                                <TrendingUp className="h-4 w-4 text-purple-600" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold truncate">{analytics?.top_selling_commodity || '-'}</div>
                            </CardContent>
                        </Card>
                    </div>

                    <Card>
                        <CardHeader>
                            <CardTitle>Recent Transactions</CardTitle>
                            <CardDescription>History of your sold produce.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-10">
                                                <Checkbox
                                                    checked={!!sales?.length && selectedIds.size === sales.length}
                                                    onCheckedChange={() => toggleSelectAll((sales ?? []).map((s) => s.id))}
                                                    aria-label="Select all"
                                                />
                                            </TableHead>
                                            <TableHead>Date</TableHead>
                                            <TableHead>Commodity</TableHead>
                                            <TableHead>Quantity</TableHead>
                                            <TableHead>Price/kg</TableHead>
                                            <TableHead>Total</TableHead>
                                            <TableHead>Buyer</TableHead>
                                            <TableHead className="text-right">Actions</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {isLoading ? (
                                            <TableRow><TableCell colSpan={8} className="text-center">Loading sales...</TableCell></TableRow>
                                        ) : sales?.length === 0 ? (
                                            <TableRow><TableCell colSpan={8} className="text-center h-24">No sales recorded yet.</TableCell></TableRow>
                                        ) : (
                                            sales?.map((sale) => (
                                                <TableRow
                                                    key={sale.id}
                                                    className={selectedIds.has(sale.id) ? 'bg-blue-50 dark:bg-blue-950/30' : undefined}
                                                >
                                                    <TableCell>
                                                        <Checkbox
                                                            checked={selectedIds.has(sale.id)}
                                                            onCheckedChange={() => toggleSelect(sale.id)}
                                                            aria-label={`Select sale ${sale.id}`}
                                                        />
                                                    </TableCell>
                                                    <TableCell>{new Date(sale.sale_date).toLocaleDateString()}</TableCell>
                                                    <TableCell className="font-medium">{sale.commodity_name || 'Loading...'}</TableCell>
                                                    <TableCell>{sale.quantity} {sale.unit}</TableCell>
                                                    <TableCell>₹{sale.price_per_unit}</TableCell>
                                                    <TableCell className="text-green-600 font-bold">₹{sale.total_amount.toLocaleString()}</TableCell>
                                                    <TableCell>{sale.buyer_name || '-'}</TableCell>
                                                    <TableCell className="text-right">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            className="text-red-500 hover:text-red-600 hover:bg-red-50"
                                                            onClick={() => {
                                                                if (window.confirm('Delete this sale record?')) {
                                                                    deleteMutation.mutate(sale.id);
                                                                }
                                                            }}
                                                            disabled={deleteMutation.isPending}
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
                </main>
            </div>
        </div>
    );
}
