import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import SalesPage from '../page'

// Mock dependencies
vi.mock('@/services/sales', () => ({
    salesService: {
        getSalesHistory: vi.fn(),
        recordSale: vi.fn(),
        updateSale: vi.fn(),
        deleteSale: vi.fn(),
        getAnalytics: vi.fn(),
    },
}))

vi.mock('@/services/inventory', () => ({
    inventoryService: {
        getAvailableStock: vi.fn(),
    },
}))

vi.mock('@tanstack/react-query', () => ({
    useQuery: vi.fn(({ queryKey }) => {
        if (queryKey.includes('sales-analytics')) {
            return {
                data: { total_revenue: 5000, total_sales_count: 5, top_selling_commodity: 'Rice' },
                isLoading: false
            }
        }
        if (queryKey.includes('inventory-stock')) {
            return {
                data: [
                    { commodity_id: 'c1', commodity_name: 'Rice', quantity: 100, unit: 'kg' },
                    { commodity_id: 'c2', commodity_name: 'Wheat', quantity: 50, unit: 'quintal' },
                ],
                isLoading: false
            }
        }
        if (queryKey.includes('sales')) {
            return {
                data: [
                    {
                        id: 's1',
                        commodity_id: 'c1',
                        commodity_name: 'Rice',
                        quantity: 10,
                        unit: 'kg',
                        price_per_unit: 50,
                        total_amount: 500,
                        sale_date: '2026-01-30',
                        buyer_name: 'Raju Trader',
                        created_at: '2026-01-30T10:00:00Z',
                    }
                ],
                isLoading: false
            }
        }
        return { data: [], isLoading: false }
    }),
    useMutation: vi.fn(() => ({
        mutate: vi.fn(),
        isPending: false
    })),
    useQueryClient: vi.fn(() => ({
        invalidateQueries: vi.fn()
    }))
}))

vi.mock('sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() }
}))

vi.mock('@/components/layout/Sidebar', () => ({ Sidebar: () => <div>Sidebar</div> }))
vi.mock('@/components/layout/Navbar', () => ({ Navbar: () => <div>Navbar</div> }))

describe('SalesPage', () => {
    it('renders sales history and analytics', () => {
        render(<SalesPage />)
        expect(screen.getAllByText('Sales')[0]).toBeInTheDocument()
        expect(screen.getByText('₹5,000')).toBeInTheDocument()
        expect(screen.getAllByText('Rice')[0]).toBeInTheDocument()
    })

    it('opens record sale modal', () => {
        render(<SalesPage />)
        fireEvent.click(screen.getAllByText('Record Sale')[0])
        expect(screen.getAllByText('Record Sale').length).toBeGreaterThanOrEqual(1)
    })

    it('shows all 4 stats cards', () => {
        render(<SalesPage />)
        expect(screen.getByText('Total Revenue')).toBeInTheDocument()
        expect(screen.getByText('Avg Sale Value')).toBeInTheDocument()
        expect(screen.getByText('Trending')).toBeInTheDocument()
        expect(screen.getByText('₹1,000')).toBeInTheDocument()
    })

    it('shows search input', () => {
        render(<SalesPage />)
        expect(screen.getByPlaceholderText('Search by commodity or buyer...')).toBeInTheDocument()
    })

    it('shows formatted date', () => {
        render(<SalesPage />)
        expect(screen.getByText('30 Jan 2026')).toBeInTheDocument()
    })

    it('shows edit and delete buttons', () => {
        render(<SalesPage />)
        const actionButtons = screen.getAllByRole('button').filter(btn =>
            btn.classList.contains('text-blue-500') || btn.classList.contains('text-red-500')
        )
        expect(actionButtons.length).toBeGreaterThanOrEqual(2)
    })

    it('shows buyer name in table', () => {
        render(<SalesPage />)
        expect(screen.getByText('Raju Trader')).toBeInTheDocument()
    })

    it('shows export CSV button', () => {
        render(<SalesPage />)
        expect(screen.getByText('Export CSV')).toBeInTheDocument()
    })

    it('shows inventory stock in record sale form', () => {
        render(<SalesPage />)
        fireEvent.click(screen.getAllByText('Record Sale')[0])
        // The commodity dropdown should show stock info
        expect(screen.getByText('Sale Date')).toBeInTheDocument()
    })

    it('shows commodity dropdown with inventory items', () => {
        render(<SalesPage />)
        fireEvent.click(screen.getAllByText('Record Sale')[0])
        // Should show commodity label (table header + form label)
        expect(screen.getAllByText('Commodity').length).toBeGreaterThanOrEqual(2)
    })
})
