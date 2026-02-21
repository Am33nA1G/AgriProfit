import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import InventoryPage from '../page'
import { inventoryService } from '@/services/inventory'
import { commoditiesService } from '@/services/commodities'

// Mock dependencies
vi.mock('@/services/inventory', () => ({
    inventoryService: {
        getInventory: vi.fn(),
        addInventory: vi.fn(),
        updateInventory: vi.fn(),
        deleteInventory: vi.fn(),
    },
}))

vi.mock('@/services/commodities', () => ({
    commoditiesService: {
        getAll: vi.fn(),
        getTopCommodities: vi.fn(),
    },
}))

vi.mock('@tanstack/react-query', () => ({
    useQuery: vi.fn(({ queryKey }) => {
        if (queryKey.includes('inventory')) {
            return {
                data: [
                    { id: '1', commodity_id: 'c1', commodity_name: 'Rice', quantity: 100, unit: 'kg', created_at: '2026-02-01T10:00:00Z', updated_at: '2026-02-01T10:00:00Z' }
                ],
                isLoading: false
            }
        }
        if (queryKey.includes('commodities')) {
            return {
                data: [
                    { id: 'c1', name: 'Rice' },
                    { id: 'c2', name: 'Wheat' }
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

describe('InventoryPage', () => {
    it('renders inventory list', () => {
        render(<InventoryPage />)
        expect(screen.getByText('Inventory')).toBeInTheDocument()
        expect(screen.getByText('Rice')).toBeInTheDocument()
        // formatQuantity: 100 kg → "100 kg (1 qtl)"
        expect(screen.getByText('100 kg (1 qtl)')).toBeInTheDocument()
        expect(screen.getByText('kg')).toBeInTheDocument()
    })

    it('opens add inventory modal', () => {
        render(<InventoryPage />)
        fireEvent.click(screen.getByText('Add Item'))
        expect(screen.getByText('Add Inventory')).toBeInTheDocument()
    })

    it('shows stats bar with item count', () => {
        render(<InventoryPage />)
        // Stats bar shows Total Items and Commodities headings
        expect(screen.getByText('Total Items')).toBeInTheDocument()
        expect(screen.getByText('Commodities')).toBeInTheDocument()
        expect(screen.getByText('Last Updated')).toBeInTheDocument()
    })

    it('shows date column', () => {
        render(<InventoryPage />)
        expect(screen.getByText('Added on')).toBeInTheDocument()
    })

    it('shows search input', () => {
        render(<InventoryPage />)
        expect(screen.getByPlaceholderText('Search by commodity name...')).toBeInTheDocument()
    })

    it('shows edit and delete buttons', () => {
        render(<InventoryPage />)
        // Edit (pencil) and Delete (trash) icon buttons
        const buttons = screen.getAllByRole('button')
        // Should have edit and delete action buttons in the row
        expect(buttons.length).toBeGreaterThan(2)
    })
})
