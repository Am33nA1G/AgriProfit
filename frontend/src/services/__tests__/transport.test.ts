import { describe, it, expect, vi, beforeEach } from 'vitest';
import { transportService } from '../transport';
import api from '@/lib/api';

vi.mock('@/lib/api');

describe('Transport Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('compareCosts()', () => {
    const validRequest = {
      commodity: 'Wheat',
      quantity_kg: 1000,
      source_state: 'Kerala',
      source_district: 'Ernakulam',
    };

    it('calls API with correct payload', async () => {
      const mockResponse = {
        commodity: 'Wheat',
        quantity_kg: 1000,
        source_district: 'Ernakulam',
        comparisons: [],
        best_mandi: null,
        total_mandis_analyzed: 0,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      await transportService.compareCosts(validRequest);

      expect(api.post).toHaveBeenCalledWith('/transport/compare', {
        commodity: 'Wheat',
        quantity_kg: 1000,
        source_state: 'Kerala',
        source_district: 'Ernakulam',
      });
    });

    it('returns comparison results with multiple options', async () => {
      const mockComparison1 = {
        mandi_id: null,
        mandi_name: 'Local Mandi',
        state: 'Kerala',
        district: 'Ernakulam',
        distance_km: 14.0,
        price_per_kg: 25,
        gross_revenue: 25000,
        costs: {
          transport_cost: 504,
          toll_cost: 200,
          loading_cost: 35,
          unloading_cost: 30,
          mandi_fee: 375,
          commission: 625,
          additional_cost: 200,
          total_cost: 1969,
        },
        net_profit: 23031,
        profit_per_kg: 23.03,
        roi_percentage: 1169.7,
        vehicle_type: 'TEMPO' as const,
        vehicle_capacity_kg: 2000,
        trips_required: 1,
        recommendation: 'recommended' as const,
      };
      const mockComparison2 = {
        ...mockComparison1,
        mandi_name: 'Distant Mandi',
        state: 'Tamil Nadu',
        district: 'Coimbatore',
        distance_km: 210.0,
        price_per_kg: 35,
        gross_revenue: 35000,
        net_profit: 27925,
        vehicle_type: 'TRUCK_SMALL' as const,
      };
      const mockResponse = {
        commodity: 'Wheat',
        quantity_kg: 1000,
        source_district: 'Ernakulam',
        comparisons: [mockComparison2, mockComparison1],
        best_mandi: mockComparison2,
        total_mandis_analyzed: 2,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await transportService.compareCosts(validRequest);

      expect(result.comparisons).toHaveLength(2);
      expect(result.best_mandi).toBeDefined();
      expect(result.best_mandi?.net_profit).toBe(27925);
    });

    it('throws on API error', async () => {
      vi.mocked(api.post).mockRejectedValue(new Error('Network error'));

      await expect(transportService.compareCosts(validRequest)).rejects.toThrow('Network error');
    });

    it('returns cost breakdown in response', async () => {
      const mockResponse = {
        commodity: 'Wheat',
        quantity_kg: 1000,
        source_district: 'Ernakulam',
        comparisons: [
          {
            mandi_id: null,
            mandi_name: 'Test Mandi',
            state: 'Kerala',
            district: 'Thrissur',
            distance_km: 70.0,
            price_per_kg: 30,
            gross_revenue: 30000,
            costs: {
              transport_cost: 2520,
              toll_cost: 200,
              loading_cost: 35,
              unloading_cost: 30,
              mandi_fee: 450,
              commission: 750,
              additional_cost: 200,
              total_cost: 4185,
            },
            net_profit: 25815,
            profit_per_kg: 25.82,
            roi_percentage: 616.7,
            vehicle_type: 'TEMPO' as const,
            vehicle_capacity_kg: 2000,
            trips_required: 1,
            recommendation: 'recommended' as const,
          },
        ],
        best_mandi: null,
        total_mandis_analyzed: 1,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await transportService.compareCosts(validRequest);

      const comparison = result.comparisons[0];
      expect(comparison.costs.transport_cost).toBeDefined();
      expect(comparison.costs.loading_cost).toBeDefined();
      expect(comparison.costs.unloading_cost).toBeDefined();
      expect(comparison.costs.mandi_fee).toBeDefined();
      expect(comparison.costs.commission).toBeDefined();
      expect(comparison.costs.total_cost).toBeDefined();
      expect(comparison.gross_revenue).toBe(30000);
    });

    it('returns null best_mandi when no results', async () => {
      const mockResponse = {
        commodity: 'Wheat',
        quantity_kg: 1000,
        source_district: 'Ernakulam',
        comparisons: [],
        best_mandi: null,
        total_mandis_analyzed: 0,
      };
      vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

      const result = await transportService.compareCosts(validRequest);

      expect(result.best_mandi).toBeNull();
    });
  });

  describe('getStates()', () => {
    it('returns list of states from API', async () => {
      const mockStates = ['Kerala', 'Tamil Nadu', 'Karnataka'];
      vi.mocked(api.get).mockResolvedValue({ data: mockStates });

      const result = await transportService.getStates();

      expect(api.get).toHaveBeenCalledWith('/mandis/states');
      expect(Array.isArray(result)).toBe(true);
      expect(result).toContain('Kerala');
    });

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'));

      await expect(transportService.getStates()).rejects.toThrow('API Error');
    });
  });

  describe('getDistricts()', () => {
    it('returns districts for a state from API', async () => {
      const mockDistricts = ['Ernakulam', 'Thrissur', 'Kozhikode'];
      vi.mocked(api.get).mockResolvedValue({ data: mockDistricts });

      const result = await transportService.getDistricts('Kerala');

      expect(api.get).toHaveBeenCalledWith('/mandis/districts', { params: { state: 'Kerala' } });
      expect(Array.isArray(result)).toBe(true);
      expect(result).toContain('Ernakulam');
    });

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'));

      await expect(transportService.getDistricts('Kerala')).rejects.toThrow('API Error');
    });
  });

  describe('getVehicles()', () => {
    it('returns vehicle options', async () => {
      const mockResponse = {
        vehicles: {
          TEMPO: { capacity_kg: 2000, cost_per_km: 18, description: 'Tata Ace' },
          TRUCK_SMALL: { capacity_kg: 7000, cost_per_km: 28, description: 'LCV' },
          TRUCK_LARGE: { capacity_kg: 15000, cost_per_km: 38, description: 'HCV' },
        },
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await transportService.getVehicles();

      expect(api.get).toHaveBeenCalledWith('/transport/vehicles');
      expect(result.TEMPO).toBeDefined();
      expect(result.TEMPO.capacity_kg).toBe(2000);
    });
  });

  describe('Route calculations', () => {
    it('estimates delivery time based on distance', () => {
      const distance = 150;
      const estimatedTime = distance / 50;
      expect(estimatedTime).toBeCloseTo(3, 1);
    });
  });
});
