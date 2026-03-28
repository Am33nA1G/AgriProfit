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
                    { id: '1', commodity_name: 'Rice', quantity: 100, unit: 'kg' }
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
        expect(screen.getByText('My Inventory')).toBeInTheDocument()
        expect(screen.getByText('Rice')).toBeInTheDocument()
        expect(screen.getByText('100')).toBeInTheDocument()
        expect(screen.getByText('kg')).toBeInTheDocument()
    })

    it('opens add inventory modal', () => {
        render(<InventoryPage />)
        fireEvent.click(screen.getByText('Add Stock'))
        expect(screen.getByText('Add Inventory')).toBeInTheDocument()
    })
})
