import api, { apiWithLongTimeout } from '@/lib/api';
import type {
    Commodity,
    CommodityWithPrice,
    CommodityDetail,
    CommoditiesWithPriceResponse
} from '@/types';

export interface CommodityFilters {
    search?: string;
    categories?: string[];
    minPrice?: number;
    maxPrice?: number;
    trend?: 'rising' | 'falling' | 'stable';
    inSeason?: boolean;
    sortBy?: 'name' | 'price' | 'change';
    sortOrder?: 'asc' | 'desc';
    skip?: number;
    limit?: number;
}

export const commoditiesService = {
    /**
     * Get all commodities (basic list)
     */
    async getAll(options?: { limit?: number }): Promise<Commodity[]> {
        const params = new URLSearchParams();
        if (options?.limit) params.append('limit', options.limit.toString());
        const queryString = params.toString();
        const url = queryString ? `/commodities/?${queryString}` : '/commodities/';
        const response = await api.get<Commodity[]>(url);
        return response.data;
    },

    /**
     * Get all unique categories
     */
    async getCategories(): Promise<string[]> {
        const response = await api.get<string[]>('/commodities/categories');
        return response.data;
    },

    /**
     * Get commodities with price data and advanced filtering
     */
    async getWithPrices(filters: CommodityFilters = {}): Promise<CommoditiesWithPriceResponse> {
        const params = new URLSearchParams();

        if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
        if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
        if (filters.search) params.append('search', filters.search);
        if (filters.categories?.length) params.append('categories', filters.categories.join(','));
        if (filters.minPrice !== undefined) params.append('min_price', filters.minPrice.toString());
        if (filters.maxPrice !== undefined) params.append('max_price', filters.maxPrice.toString());
        if (filters.trend) params.append('trend', filters.trend);
        if (filters.inSeason !== undefined) params.append('in_season', filters.inSeason.toString());
        if (filters.sortBy) params.append('sort_by', filters.sortBy);
        if (filters.sortOrder) params.append('sort_order', filters.sortOrder);

        const queryString = params.toString();
        const url = queryString ? `/commodities/with-prices?${queryString}` : '/commodities/with-prices';

        const response = await api.get<CommoditiesWithPriceResponse>(url);
        return response.data;
    },

    /**
     * Get detailed commodity information (uses longer timeout for heavy queries)
     */
    async getDetails(commodityId: string): Promise<CommodityDetail> {
        const response = await apiWithLongTimeout.get<CommodityDetail>(`/commodities/${commodityId}/details`);
        return response.data;
    },

    /**
     * Compare multiple commodities
     */
    async compare(commodityIds: string[]): Promise<{ commodities: CommodityDetail[]; comparison_date: string }> {
        const response = await api.post<{ commodities: CommodityDetail[]; comparison_date: string }>(
            '/commodities/compare',
            commodityIds
        );
        return response.data;
    },

    /**
     * Get a single commodity by ID
     */
    async getById(id: string): Promise<Commodity> {
        const response = await api.get<Commodity>(`/commodities/${id}`);
        return response.data;
    },

    /**
     * Search commodities by name
     */
    async search(query: string, limit: number = 10): Promise<Commodity[]> {
        const response = await api.get<Commodity[]>(
            `/commodities/search/?q=${encodeURIComponent(query)}&limit=${limit}`
        );
        return response.data;
    },

    /**
     * Get top commodities by highest price
     */
    async getTopCommodities(limit: number = 5): Promise<CommodityWithPrice[]> {
        const response = await this.getWithPrices({
            sortBy: 'price',
            sortOrder: 'desc',
            limit,
        });
        return response.commodities;
    },
};
