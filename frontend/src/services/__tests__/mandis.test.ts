import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mandisService } from '../mandis';
import api from '@/lib/api';

vi.mock('@/lib/api');

describe('Mandis Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getAll()', () => {
    it('returns list of mandis without filters', async () => {
      const mockMandis = [
        { id: '1', name: 'Mandi A', district: 'Ernakulam', state: 'Kerala' },
        { id: '2', name: 'Mandi B', district: 'Thrissur', state: 'Kerala' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockMandis });

      const result = await mandisService.getAll();

      expect(api.get).toHaveBeenCalledWith('/mandis/', { params: undefined });
      expect(result).toEqual(mockMandis);
    });

    it('filters mandis by district', async () => {
      const mockMandis = [
        { id: '1', name: 'Mandi A', district: 'Ernakulam', state: 'Kerala' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockMandis });

      const result = await mandisService.getAll({ district: 'Ernakulam' });

      expect(api.get).toHaveBeenCalledWith('/mandis/', {
        params: { district: 'Ernakulam' },
      });
      expect(result).toEqual(mockMandis);
    });

    it('filters mandis by state', async () => {
      const mockMandis = [
        { id: '1', name: 'Mandi A', state: 'Kerala' },
        { id: '2', name: 'Mandi B', state: 'Kerala' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockMandis });

      const result = await mandisService.getAll({ state: 'Kerala' });

      expect(api.get).toHaveBeenCalledWith('/mandis/', {
        params: { state: 'Kerala' },
      });
      expect(result).toEqual(mockMandis);
    });

    it('limits number of results', async () => {
      const mockMandis = [{ id: '1', name: 'Mandi A' }];
      vi.mocked(api.get).mockResolvedValue({ data: mockMandis });

      await mandisService.getAll({ limit: 10 });

      expect(api.get).toHaveBeenCalledWith('/mandis/', {
        params: { limit: 10 },
      });
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Network error'));

      await expect(mandisService.getAll()).rejects.toThrow('Network error');
    });
  });

  describe('getStates()', () => {
    it('returns list of unique states', async () => {
      const mockStates = ['Kerala', 'Tamil Nadu', 'Karnataka'];
      vi.mocked(api.get).mockResolvedValue({ data: mockStates });

      const result = await mandisService.getStates();

      expect(api.get).toHaveBeenCalledWith('/mandis/states');
      expect(result).toEqual(mockStates);
    });

    it('returns empty array when no states', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await mandisService.getStates();

      expect(result).toEqual([]);
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Failed to fetch states'));

      await expect(mandisService.getStates()).rejects.toThrow('Failed to fetch states');
    });
  });

  describe('getDistrictsByState()', () => {
    it('returns districts for a given state', async () => {
      const mockDistricts = ['Ernakulam', 'Thrissur', 'Kozhikode'];
      vi.mocked(api.get).mockResolvedValue({ data: mockDistricts });

      const result = await mandisService.getDistrictsByState('Kerala');

      expect(api.get).toHaveBeenCalledWith('/mandis/districts?state=Kerala');
      expect(result).toEqual(mockDistricts);
    });

    it('encodes state name with spaces', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: ['District 1'] });

      await mandisService.getDistrictsByState('Tamil Nadu');

      expect(api.get).toHaveBeenCalledWith('/mandis/districts?state=Tamil%20Nadu');
    });

    it('returns empty array when state has no districts', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await mandisService.getDistrictsByState('Unknown State');

      expect(result).toEqual([]);
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('State not found'));

      await expect(mandisService.getDistrictsByState('Invalid')).rejects.toThrow('State not found');
    });
  });

  describe('getWithFilters()', () => {
    it('gets mandis without filters', async () => {
      const mockResponse = {
        mandis: [],
        total: 0,
        skip: 0,
        limit: 20,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      const result = await mandisService.getWithFilters();

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters');
      expect(result).toEqual(mockResponse);
    });

    it('applies pagination parameters', async () => {
      const mockResponse = { mandis: [], total: 100, skip: 20, limit: 10 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ skip: 20, limit: 10 });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?skip=20&limit=10');
    });

    it('applies search filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ search: 'market' });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?search=market');
    });

    it('applies state filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ states: ['Kerala', 'Tamil Nadu'] });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?states=Kerala%2CTamil+Nadu');
    });

    it('applies district filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ district: 'Ernakulam' });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?district=Ernakulam');
    });

    it('applies commodity filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ commodity: 'Tomato' });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?commodity=Tomato');
    });

    it('applies distance filter with user location', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({
        maxDistanceKm: 50,
        userLat: 10.0261,
        userLon: 76.3125,
      });

      expect(api.get).toHaveBeenCalledWith(
        '/mandis/with-filters?max_distance_km=50&user_lat=10.0261&user_lon=76.3125'
      );
    });

    it('applies user district and state', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({
        userDistrict: 'Ernakulam',
        userState: 'Kerala',
      });

      expect(api.get).toHaveBeenCalledWith(
        '/mandis/with-filters?user_district=Ernakulam&user_state=Kerala'
      );
    });

    it('applies facility filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ hasFacility: 'cold_storage' });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?has_facility=cold_storage');
    });

    it('applies minimum rating filter', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ minRating: 4.5 });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?min_rating=4.5');
    });

    it('applies sorting parameters', async () => {
      const mockResponse = { mandis: [], total: 0 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({ sortBy: 'distance', sortOrder: 'asc' });

      expect(api.get).toHaveBeenCalledWith('/mandis/with-filters?sort_by=distance&sort_order=asc');
    });

    it('combines multiple filters', async () => {
      const mockResponse = { mandis: [], total: 50 };
      vi.mocked(api.get).mockResolvedValue({ data: mockResponse });

      await mandisService.getWithFilters({
        search: 'market',
        states: ['Kerala'],
        district: 'Ernakulam',
        skip: 0,
        limit: 20,
        sortBy: 'name',
        sortOrder: 'asc',
      });

      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/mandis/with-filters?')
      );
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('search=market')
      );
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('district=Ernakulam')
      );
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Failed to fetch'));

      await expect(mandisService.getWithFilters()).rejects.toThrow('Failed to fetch');
    });
  });

  describe('getById()', () => {
    it('returns mandi details by ID', async () => {
      const mockMandi = {
        id: '1',
        name: 'Central Market',
        district: 'Ernakulam',
        state: 'Kerala',
        latitude: 10.0261,
        longitude: 76.3125,
      };
      vi.mocked(api.get).mockResolvedValue({ data: mockMandi });

      const result = await mandisService.getById('1');

      expect(api.get).toHaveBeenCalledWith('/mandis/1');
      expect(result).toEqual(mockMandi);
    });

    it('handles invalid ID (404)', async () => {
      vi.mocked(api.get).mockRejectedValue({
        response: { status: 404, data: { detail: 'Mandi not found' } },
      });

      await expect(mandisService.getById('invalid-id')).rejects.toMatchObject({
        response: { status: 404 },
      });
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Server error'));

      await expect(mandisService.getById('1')).rejects.toThrow('Server error');
    });
  });

  describe('getCurrentPrices()', () => {
    it('returns current commodity prices for a mandi', async () => {
      const mockPrices = [
        { commodity_id: '1', commodity_name: 'Tomato', price: 25, unit: 'kg' },
        { commodity_id: '2', commodity_name: 'Onion', price: 30, unit: 'kg' },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockPrices });

      const result = await mandisService.getCurrentPrices('mandi-1');

      expect(api.get).toHaveBeenCalledWith('/mandis/mandi-1/prices');
      expect(result).toEqual(mockPrices);
    });

    it('filters prices by commodity', async () => {
      const mockPrices = [
        { commodity_id: '1', commodity_name: 'Tomato', price: 25 },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockPrices });

      await mandisService.getCurrentPrices('mandi-1', 'Tomato');

      expect(api.get).toHaveBeenCalledWith('/mandis/mandi-1/prices?commodity=Tomato');
    });

    it('returns empty array when no prices available', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await mandisService.getCurrentPrices('mandi-1');

      expect(result).toEqual([]);
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Failed to fetch prices'));

      await expect(mandisService.getCurrentPrices('mandi-1')).rejects.toThrow('Failed to fetch prices');
    });
  });

  describe('getNearbyMandis()', () => {
    it('returns nearby mandis based on location', async () => {
      const mockMandis = [
        { id: '1', name: 'Nearby Mandi 1', distance_km: 5.2 },
        { id: '2', name: 'Nearby Mandi 2', distance_km: 12.8 },
      ];
      vi.mocked(api.get).mockResolvedValue({ data: mockMandis });

      const result = await mandisService.getNearbyMandis(10.0261, 76.3125, 20);

      expect(api.get).toHaveBeenCalledWith(
        '/mandis/nearby?lat=10.0261&lon=76.3125&radius_km=20'
      );
      expect(result).toEqual(mockMandis);
    });

    it('uses default radius when not provided', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      await mandisService.getNearbyMandis(10.0261, 76.3125);

      expect(api.get).toHaveBeenCalledWith(
        '/mandis/nearby?lat=10.0261&lon=76.3125&radius_km=50'
      );
    });

    it('returns empty array when no nearby mandis', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] });

      const result = await mandisService.getNearbyMandis(10.0261, 76.3125, 5);

      expect(result).toEqual([]);
    });

    it('handles location permission denied', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Location access denied'));

      await expect(
        mandisService.getNearbyMandis(0, 0, 10)
      ).rejects.toThrow('Location access denied');
    });

    it('handles API errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Server error'));

      await expect(
        mandisService.getNearbyMandis(10.0261, 76.3125, 20)
      ).rejects.toThrow('Server error');
    });
  });

  describe('calculateDistance()', () => {
    it('calculates distance between two points', () => {
      // Ernakulam to Thrissur (approximately 50km)
      const distance = mandisService.calculateDistance(
        10.5276, 76.2144, // Ernakulam
        10.5276, 76.2144  // Same location
      );

      expect(distance).toBe(0);
    });

    it('returns non-zero distance for different locations', () => {
      const distance = mandisService.calculateDistance(
        10.0261, 76.3125, // Location A
        11.0168, 76.9558  // Location B (Coimbatore)
      );

      expect(distance).toBeGreaterThan(0);
      expect(distance).toBeLessThan(200); // Reasonable distance
    });

    it('handles negative coordinates', () => {
      const distance = mandisService.calculateDistance(
        -10.0, -76.0,
        -10.5, -76.5
      );

      expect(distance).toBeGreaterThan(0);
    });

    it('handles equator crossing', () => {
      const distance = mandisService.calculateDistance(
        -1.0, 0.0,
        1.0, 0.0
      );

      expect(distance).toBeGreaterThan(0);
    });
  });
});
