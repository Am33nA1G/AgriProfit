import { describe, it, expect, vi, beforeEach } from 'vitest'
import { pricesService } from '../prices'
import api from '@/lib/api'

vi.mock('@/lib/api')

describe('Prices Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getCurrentPrices()', () => {
    it('fetches current prices successfully', async () => {
      const mockData = {
        prices: [
          {
            commodity_id: '1',
            commodity: 'Wheat',
            mandi_name: 'Azadpur',
            state: 'Delhi',
            district: 'North Delhi',
            price_per_kg: 28.50,
            change_percent: 5.2,
            change_amount: 1.41,
            updated_at: '2024-01-01T00:00:00Z'
          },
          {
            commodity_id: '2',
            commodity: 'Rice',
            mandi_name: 'Karnal',
            state: 'Haryana',
            district: 'Karnal',
            price_per_kg: 35.00,
            change_percent: -1.2,
            change_amount: -0.42,
            updated_at: '2024-01-01T00:00:00Z'
          }
        ]
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      const result = await pricesService.getCurrentPrices()

      expect(api.get).toHaveBeenCalledWith('/prices/current', { params: undefined })
      expect(result).toEqual(mockData)
      expect(result.prices).toHaveLength(2)
    })

    it('fetches prices with commodity filter', async () => {
      const mockData = { prices: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getCurrentPrices({ commodity: 'Wheat' })

      expect(api.get).toHaveBeenCalledWith('/prices/current', {
        params: { commodity: 'Wheat' }
      })
    })

    it('fetches prices with state filter', async () => {
      const mockData = { prices: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getCurrentPrices({ state: 'Delhi' })

      expect(api.get).toHaveBeenCalledWith('/prices/current', {
        params: { state: 'Delhi' }
      })
    })

    it('fetches prices with district filter', async () => {
      const mockData = { prices: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getCurrentPrices({ district: 'Karnal' })

      expect(api.get).toHaveBeenCalledWith('/prices/current', {
        params: { district: 'Karnal' }
      })
    })

    it('fetches prices with multiple filters', async () => {
      const mockData = { prices: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getCurrentPrices({
        commodity: 'Wheat',
        state: 'Punjab',
        district: 'Ludhiana'
      })

      expect(api.get).toHaveBeenCalledWith('/prices/current', {
        params: {
          commodity: 'Wheat',
          state: 'Punjab',
          district: 'Ludhiana'
        }
      })
    })

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'))

      await expect(pricesService.getCurrentPrices()).rejects.toThrow('API Error')
    })

    it('returns data with correct structure', async () => {
      const mockData = {
        prices: [
          {
            commodity_id: '1',
            commodity: 'Tomato',
            mandi_name: 'Azadpur',
            state: 'Delhi',
            district: 'North Delhi',
            price_per_kg: 42.00,
            change_percent: 15.2,
            change_amount: 5.60,
            updated_at: '2024-01-01T00:00:00Z'
          }
        ]
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      const result = await pricesService.getCurrentPrices()

      expect(result.prices[0]).toHaveProperty('commodity_id')
      expect(result.prices[0]).toHaveProperty('commodity')
      expect(result.prices[0]).toHaveProperty('mandi_name')
      expect(result.prices[0]).toHaveProperty('state')
      expect(result.prices[0]).toHaveProperty('district')
      expect(result.prices[0]).toHaveProperty('price_per_kg')
      expect(result.prices[0]).toHaveProperty('change_percent')
      expect(result.prices[0]).toHaveProperty('change_amount')
      expect(result.prices[0]).toHaveProperty('updated_at')
    })
  })

  describe('getHistoricalPrices()', () => {
    it('fetches historical prices successfully', async () => {
      const mockData = {
        data: [
          { date: '2024-01-01', price: 28.50 },
          { date: '2024-01-02', price: 29.00 },
          { date: '2024-01-03', price: 28.75 }
        ]
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      const result = await pricesService.getHistoricalPrices({
        commodity: 'Wheat',
        mandi_id: '123',
        days: 30
      })

      expect(api.get).toHaveBeenCalledWith('/prices/historical', {
        params: { commodity: 'Wheat', mandi_id: '123', days: 30 }
      })
      expect(result).toEqual(mockData)
      expect(result.data).toHaveLength(3)
    })

    it('fetches prices for different time periods', async () => {
      const mockData = { data: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getHistoricalPrices({
        commodity: 'Rice',
        mandi_id: '456',
        days: 7
      })

      expect(api.get).toHaveBeenCalledWith('/prices/historical', {
        params: { commodity: 'Rice', mandi_id: '456', days: 7 }
      })
    })

    it('fetches prices for 90 days', async () => {
      const mockData = { data: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getHistoricalPrices({
        commodity: 'Onion',
        mandi_id: '789',
        days: 90
      })

      expect(api.get).toHaveBeenCalledWith('/prices/historical', {
        params: { commodity: 'Onion', mandi_id: '789', days: 90 }
      })
    })

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'))

      await expect(
        pricesService.getHistoricalPrices({ commodity: 'Wheat', mandi_id: '123', days: 30 })
      ).rejects.toThrow('API Error')
    })
  })

  describe('getTopMovers()', () => {
    it('fetches top movers successfully', async () => {
      const mockData = {
        gainers: [
          { commodity: 'Tomato', change_percent: 15.2, price: 42.0 },
          { commodity: 'Potato', change_percent: 8.5, price: 18.5 }
        ],
        losers: [
          { commodity: 'Banana', change_percent: -4.5, price: 32.0 },
          { commodity: 'Garlic', change_percent: -2.3, price: 95.0 }
        ]
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      const result = await pricesService.getTopMovers()

      expect(api.get).toHaveBeenCalledWith('/prices/top-movers', { params: { limit: 5 } })
      expect(result).toEqual(mockData)
      expect(result.gainers).toHaveLength(2)
      expect(result.losers).toHaveLength(2)
    })

    it('fetches top movers with custom limit', async () => {
      const mockData = { gainers: [], losers: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getTopMovers(10)

      expect(api.get).toHaveBeenCalledWith('/prices/top-movers', { params: { limit: 10 } })
    })

    it('fetches top 3 movers', async () => {
      const mockData = { gainers: [], losers: [] }
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getTopMovers(3)

      expect(api.get).toHaveBeenCalledWith('/prices/top-movers', { params: { limit: 3 } })
    })

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'))

      await expect(pricesService.getTopMovers()).rejects.toThrow('API Error')
    })
  })

  describe('getPricesByMandi()', () => {
    it('fetches prices by mandi successfully', async () => {
      const mockData = [
        {
          commodity: 'Wheat',
          price_per_kg: 28.50,
          date: '2024-01-01'
        },
        {
          commodity: 'Rice',
          price_per_kg: 35.00,
          date: '2024-01-02'
        }
      ]

      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      const result = await pricesService.getPricesByMandi('mandi-123')

      expect(api.get).toHaveBeenCalledWith('/prices/mandi/mandi-123', {
        params: { limit: 100 }
      })
      expect(result).toEqual(mockData)
      expect(result).toHaveLength(2)
    })

    it('fetches prices with date range filter', async () => {
      const mockData: any[] = []
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getPricesByMandi('mandi-456', {
        start_date: '2024-01-01',
        end_date: '2024-01-31'
      })

      expect(api.get).toHaveBeenCalledWith('/prices/mandi/mandi-456', {
        params: {
          limit: 100,
          start_date: '2024-01-01',
          end_date: '2024-01-31'
        }
      })
    })

    it('fetches prices with custom limit', async () => {
      const mockData: any[] = []
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getPricesByMandi('mandi-789', { limit: 50 })

      expect(api.get).toHaveBeenCalledWith('/prices/mandi/mandi-789', {
        params: { limit: 50 }
      })
    })

    it('fetches prices with all parameters', async () => {
      const mockData: any[] = []
      vi.mocked(api.get).mockResolvedValue({ data: mockData })

      await pricesService.getPricesByMandi('mandi-999', {
        start_date: '2024-01-01',
        end_date: '2024-01-07',
        limit: 25
      })

      expect(api.get).toHaveBeenCalledWith('/prices/mandi/mandi-999', {
        params: {
          limit: 25,
          start_date: '2024-01-01',
          end_date: '2024-01-07'
        }
      })
    })

    it('throws on API error', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('API Error'))

      await expect(pricesService.getPricesByMandi('mandi-123')).rejects.toThrow('API Error')
    })
  })

  describe('Error Handling', () => {
    it('all methods propagate errors', async () => {
      vi.mocked(api.get).mockRejectedValue(new Error('Server Error'))

      await expect(pricesService.getCurrentPrices()).rejects.toThrow()
      await expect(pricesService.getHistoricalPrices({ commodity: 'Test', mandi_id: '1', days: 7 })).rejects.toThrow()
      await expect(pricesService.getTopMovers()).rejects.toThrow()
      await expect(pricesService.getPricesByMandi('test')).rejects.toThrow()
    })
  })
})
