import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SalesPage from '../page'
import { salesService } from '@/services/sales'
import { commoditiesService } from '@/services/commodities'

// Mock dependencies
vi.mock('@/services/sales', () => ({
    salesService: {
        getSalesHistory: vi.fn(),
        recordSale: vi.fn(),
        getAnalytics: vi.fn(),
    },
}))

vi.mock('@/services/commodities', () => ({
    commoditiesService: {
        getAll: vi.fn(),
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
        if (queryKey.includes('sales')) {
            return {
                data: [
                    { id: 's1', commodity_name: 'Rice', quantity: 10, unit: 'kg', price_per_unit: 50, total_amount: 500, sale_date: '2026-01-30' }
                ],
                isLoading: false
            }
        }
        if (queryKey.includes('commodities')) {
            return {
                data: [
                    { id: 'c1', name: 'Rice' }
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

// Mock components that use context
vi.mock('@/components/layout/Sidebar', () => ({ Sidebar: () => <div>Sidebar</div> }))
vi.mock('@/components/layout/Navbar', () => ({ Navbar: () => <div>Navbar</div> }))

describe('SalesPage', () => {
    it('renders sales history and analytics', () => {
        render(<SalesPage />)
        expect(screen.getByText('Sales & Revenue')).toBeInTheDocument()
        expect(screen.getByText('₹5,000')).toBeInTheDocument()
        expect(screen.getAllByText('Rice')[0]).toBeInTheDocument()
    })

    it('opens record sale modal', () => {
        render(<SalesPage />)
        fireEvent.click(screen.getByText('Record Sale'))
        expect(screen.getByText('Record New Sale')).toBeInTheDocument()
    })
})
