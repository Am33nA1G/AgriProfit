import { describe, it, expect, vi, beforeEach } from 'vitest';
import { inventoryService } from '../inventory';
import api from '@/lib/api';

// Mock the api module
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Inventory Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getInventory', () => {
    it('should fetch all inventory items', async () => {
      const mockInventory = [
        {
          id: '1',
          user_id: 'user1',
          commodity_id: 'comm1',
          quantity: 100,
          unit: 'kg',
          commodity_name: 'Tomato',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockInventory });

      const result = await inventoryService.getInventory();

      expect(api.get).toHaveBeenCalledWith('/inventory');
      expect(result).toEqual(mockInventory);
    });

    it('should handle empty inventory', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await inventoryService.getInventory();

      expect(result).toEqual([]);
    });
  });

  describe('addInventory', () => {
    it('should add new inventory item', async () => {
      const newItem = {
        commodity_id: 'comm1',
        quantity: 50,
        unit: 'kg',
      };
      const mockResponse = {
        id: '1',
        user_id: 'user1',
        ...newItem,
        updated_at: '2024-01-01T00:00:00Z',
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await inventoryService.addInventory(newItem);

      expect(api.post).toHaveBeenCalledWith('/inventory', newItem);
      expect(result).toEqual(mockResponse);
    });

    it('should handle validation errors', async () => {
      const invalidItem = {
        commodity_id: '',
        quantity: -10,
        unit: 'kg',
      };
      vi.mocked(api.post).mockRejectedValue(new Error('Validation error'));

      await expect(inventoryService.addInventory(invalidItem)).rejects.toThrow('Validation error');
    });
  });

  describe('deleteInventory', () => {
    it('should delete inventory item by id', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: null });

      await inventoryService.deleteInventory('1');

      expect(api.delete).toHaveBeenCalledWith('/inventory/1');
    });

    it('should handle deletion errors', async () => {
      vi.mocked(api.delete).mockRejectedValue(new Error('Not found'));

      await expect(inventoryService.deleteInventory('invalid-id')).rejects.toThrow('Not found');
    });
  });

  describe('analyzeInventory', () => {
    it('should analyze inventory and return recommendations', async () => {
      const mockAnalysis = {
        total_items: 3,
        analysis: [
          {
            commodity_id: 'comm1',
            commodity_name: 'Tomato',
            quantity: 100,
            unit: 'kg',
            best_mandis: [],
            estimated_min_revenue: 2000,
            estimated_max_revenue: 3000,
          },
        ],
        total_estimated_min_revenue: 2000,
        total_estimated_max_revenue: 3000,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockAnalysis });

      const result = await inventoryService.analyzeInventory();

      expect(api.post).toHaveBeenCalledWith('/inventory/analyze');
      expect(result).toEqual(mockAnalysis);
    });

    it('should handle empty inventory analysis', async () => {
      const mockAnalysis = {
        total_items: 0,
        analysis: [],
        total_estimated_min_revenue: 0,
        total_estimated_max_revenue: 0,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockAnalysis });

      const result = await inventoryService.analyzeInventory();

      expect(result.total_items).toBe(0);
      expect(result.analysis).toHaveLength(0);
    });
  });
});
