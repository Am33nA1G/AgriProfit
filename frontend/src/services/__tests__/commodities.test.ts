import { describe, it, expect, vi, beforeEach } from 'vitest';
import { commoditiesService } from '../commodities';
import api, { apiWithLongTimeout } from '@/lib/api';

// Mock the api modules
vi.mock('@/lib/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
  apiWithLongTimeout: {
    get: vi.fn(),
  },
}));

describe('Commodities Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getAll', () => {
    it('should fetch all commodities without limit', async () => {
      const mockCommodities = [
        { id: '1', name: 'Tomato', category: 'Vegetables' },
        { id: '2', name: 'Potato', category: 'Vegetables' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockCommodities });

      const result = await commoditiesService.getAll();

      expect(api.get).toHaveBeenCalledWith('/commodities/');
      expect(result).toEqual(mockCommodities);
    });

    it('should fetch commodities with limit', async () => {
      const mockCommodities = [{ id: '1', name: 'Tomato' }];
      vi.mocked(api.get).mockResolvedValue({ data: mockCommodities });

      const result = await commoditiesService.getAll({ limit: 10 });

      expect(api.get).toHaveBeenCalledWith('/commodities/?limit=10');
      expect(result).toEqual(mockCommodities);
    });
  });

  describe('getCategories', () => {
    it('should fetch all categories', async () => {
      const mockCategories = ['Vegetables', 'Fruits', 'Grains'];
      vi.mocked(api.get).mockResolvedValue({ data: mockCategories });

      const result = await commoditiesService.getCategories();

      expect(api.get).toHaveBeenCalledWith('/commodities/categories');
      expect(result).toEqual(mockCategories);
    });
  });

  describe('getWithPrices', () => {
    it('should fetch commodities with prices and no filters', async () => {
      const mockResponse = {
        commodities: [{ id: '1', name: 'Tomato', price: 30 }],
        total: 1,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.getWithPrices();

      expect(api.get).toHaveBeenCalledWith('/commodities/with-prices');
      expect(result).toEqual(mockResponse);
    });

    it('should apply search filter', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getWithPrices({ search: 'tomato' });

      expect(api.get).toHaveBeenCalledWith('/commodities/with-prices?search=tomato');
    });

    it('should apply pagination filters', async () => {
      const mockResponse = { commodities: [], total: 50 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getWithPrices({ skip: 10, limit: 20 });

      expect(api.get).toHaveBeenCalledWith('/commodities/with-prices?skip=10&limit=20');
    });

    it('should apply multiple filters', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getWithPrices({
        search: 'rice',
        categories: ['Grains'],
        minPrice: 50,
        maxPrice: 100,
        trend: 'rising',
      });

      const url = vi.mocked(api.get).mock.calls[0][0];
      expect(url).toContain('search=rice');
      expect(url).toContain('categories=Grains');
      expect(url).toContain('min_price=50');
      expect(url).toContain('max_price=100');
      expect(url).toContain('trend=rising');
    });

    it('should apply sorting parameters', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getWithPrices({ sortBy: 'price', sortOrder: 'desc' });

      const url = vi.mocked(api.get).mock.calls[0][0];
      expect(url).toContain('sort_by=price');
      expect(url).toContain('sort_order=desc');
    });

    it('should filter by season', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getWithPrices({ inSeason: true });

      expect(api.get).toHaveBeenCalledWith('/commodities/with-prices?in_season=true');
    });
  });

  describe('getDetails', () => {
    it('should fetch detailed commodity information', async () => {
      const mockDetail = {
        id: '1',
        name: 'Tomato',
        category: 'Vegetables',
        price_history: [],
        forecast: null,
      };
      vi.mocked(apiWithLongTimeout.get).mockResolvedValue({ data: mockDetail });

      const result = await commoditiesService.getDetails('1');

      expect(apiWithLongTimeout.get).toHaveBeenCalledWith('/commodities/1/details');
      expect(result).toEqual(mockDetail);
    });

    it('should use long timeout for heavy queries', async () => {
      const mockDetail = { id: '1', name: 'Tomato' };
      vi.mocked(apiWithLongTimeout.get).mockResolvedValue({ data: mockDetail });

      await commoditiesService.getDetails('1');

      expect(apiWithLongTimeout.get).toHaveBeenCalled();
    });

    it('should handle invalid commodity ID', async () => {
      vi.mocked(apiWithLongTimeout.get).mockRejectedValue({
        response: { status: 404, data: { detail: 'Commodity not found' } },
      });

      await expect(commoditiesService.getDetails('invalid')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });
  });

  describe('compare', () => {
    it('should compare multiple commodities', async () => {
      const mockResponse = {
        commodities: [
          { id: '1', name: 'Tomato', price: 30 },
          { id: '2', name: 'Potato', price: 25 },
        ],
        comparison_date: '2024-01-01',
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.compare(['1', '2']);

      expect(api.post).toHaveBeenCalledWith('/commodities/compare', ['1', '2']);
      expect(result).toEqual(mockResponse);
    });

    it('should handle empty commodity list', async () => {
      const mockResponse = { commodities: [], comparison_date: '2024-01-01' };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.compare([]);

      expect(result.commodities).toHaveLength(0);
    });

    it('should handle partial failures in comparison', async () => {
      const mockResponse = {
        commodities: [{ id: '1', name: 'Tomato', price: 30 }],
        comparison_date: '2024-01-01',
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.compare(['1', 'invalid-id']);

      expect(result.commodities).toHaveLength(1);
    });
  });

  describe('getById', () => {
    it('should fetch single commodity by ID', async () => {
      const mockCommodity = { id: '1', name: 'Tomato', category: 'Vegetables' };
      vi.mocked(api.get).mockResolvedValue({ data: mockCommodity });

      const result = await commoditiesService.getById('1');

      expect(api.get).toHaveBeenCalledWith('/commodities/1');
      expect(result).toEqual(mockCommodity);
    });

    it('should handle 404 for non-existent commodity', async () => {
      vi.mocked(api.get).mockRejectedValue({
        response: { status: 404, data: { detail: 'Commodity not found' } },
      });

      await expect(commoditiesService.getById('999')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });
  });

  describe('search', () => {
    it('should search commodities by name', async () => {
      const mockResults = [
        { id: '1', name: 'Tomato', category: 'Vegetables' },
        { id: '2', name: 'Cherry Tomato', category: 'Vegetables' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockResults });

      const result = await commoditiesService.search('tomato');

      expect(api.get).toHaveBeenCalledWith('/commodities/search/?q=tomato&limit=10');
      expect(result).toEqual(mockResults);
    });

    it('should apply custom limit', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await commoditiesService.search('rice', 5);

      expect(api.get).toHaveBeenCalledWith('/commodities/search/?q=rice&limit=5');
    });

    it('should encode special characters in search query', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await commoditiesService.search('rice & wheat');

      const url = vi.mocked(api.get).mock.calls[0][0];
      expect(url).toContain(encodeURIComponent('rice & wheat'));
    });

    it('should return empty array when no results', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await commoditiesService.search('nonexistent');

      expect(result).toEqual([]);
    });
  });

  describe('getTopCommodities', () => {
    it('should fetch top commodities by price', async () => {
      const mockResponse = {
        commodities: [
          { id: '1', name: 'Saffron', price: 500 },
          { id: '2', name: 'Cardamom', price: 300 },
        ],
        total: 2,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.getTopCommodities();

      const url = vi.mocked(api.get).mock.calls[0][0];
      expect(url).toContain('sort_by=price');
      expect(url).toContain('sort_order=desc');
      expect(url).toContain('limit=5');
      expect(result).toEqual(mockResponse.commodities);
    });

    it('should apply custom limit', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await commoditiesService.getTopCommodities(10);

      const url = vi.mocked(api.get).mock.calls[0][0];
      expect(url).toContain('limit=10');
    });

    it('should return empty array when no commodities', async () => {
      const mockResponse = { commodities: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await commoditiesService.getTopCommodities();

      expect(result).toEqual([]);
    });
  });

  describe('Edge Cases', () => {
    it('should handle concurrent requests', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await Promise.all([
        commoditiesService.getAll(),
        commoditiesService.getCategories(),
        commoditiesService.search('test'),
      ]);

      expect(api.get).toHaveBeenCalledTimes(3);
    });

    it('should handle zero limit gracefully', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await commoditiesService.getAll({ limit: 0 });

      expect(api.get).toHaveBeenCalled();
      const url = vi.mocked(api.get).mock.calls[0][0];
      // Zero limit still creates URL parameter
      expect(url).toBeDefined();
    });

    it('should handle very long search queries', async () => {
      const longQuery = 'a'.repeat(500);
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await commoditiesService.search(longQuery);

      expect(api.get).toHaveBeenCalled();
    });

    it('should handle numeric commodity IDs', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { id: '123', name: 'Test' } });

      await commoditiesService.getById('123');

      expect(api.get).toHaveBeenCalledWith('/commodities/123');
    });

    it('should handle string commodity IDs with special chars', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { id: 'uuid-123-abc', name: 'Test' } });

      await commoditiesService.getById('uuid-123-abc');

      expect(api.get).toHaveBeenCalledWith('/commodities/uuid-123-abc');
    });
  });
});
