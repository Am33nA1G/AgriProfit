// mobile/src/store/inventoryStore.ts
// Shared zustand store for crop inventory.
// Extracted from InventoryScreen so InventoryAnalysisScreen can read the same data.

import { create } from 'zustand';

export interface InventoryItem {
    id: string;
    crop: string;
    quantity: string;   // numeric string, kg/quintal/ton/piece
    unit: string;
    pricePerUnit: string; // ₹ per unit
    notes: string;
}

interface InventoryState {
    items: InventoryItem[];
    addItem: (data: Omit<InventoryItem, 'id'>) => void;
    updateItem: (id: string, updates: Omit<InventoryItem, 'id'>) => void;
    deleteItem: (id: string) => void;
}

export const useInventoryStore = create<InventoryState>()((set) => ({
    items: [
        { id: '1', crop: 'Tomato', quantity: '200', unit: 'kg', pricePerUnit: '25', notes: 'Stored in cold room' },
        { id: '2', crop: 'Onion', quantity: '500', unit: 'kg', pricePerUnit: '18', notes: '' },
    ],

    addItem: (data) =>
        set((state) => ({
            items: [...state.items, { id: Date.now().toString(), ...data }],
        })),

    updateItem: (id, updates) =>
        set((state) => ({
            items: state.items.map((it) => (it.id === id ? { ...it, ...updates } : it)),
        })),

    deleteItem: (id) =>
        set((state) => ({
            items: state.items.filter((it) => it.id !== id),
        })),
}));
