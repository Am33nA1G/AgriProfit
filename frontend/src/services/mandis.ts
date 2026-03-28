import api from '@/lib/api';
import type {
    Mandi,
    MandiWithDistance,
    MandiDetail,
    MandisWithFiltersResponse
} from '@/types';

export interface MandiFilters {
    search?: string;
    states?: string[];
    district?: string;
    commodity?: string;
    maxDistanceKm?: number;
    userLat?: number;
    userLon?: number;
    userDistrict?: string;
    userState?: string;
    hasFacility?: 'weighbridge' | 'storage' | 'loading_dock' | 'cold_storage';
    minRating?: number;
    sortBy?: 'name' | 'distance' | 'rating';
    sortOrder?: 'asc' | 'desc';
    skip?: number;
    limit?: number;
}

export const mandisService = {
    /**
     * Get all mandis (basic list)
     */
    async getAll(params?: { district?: string; state?: string; limit?: number }): Promise<Mandi[]> {
        const response = await api.get<Mandi[]>('/mandis/', { params });
        return response.data;
    },

    /**
     * Get all unique states
     */
    async getStates(): Promise<string[]> {
        const response = await api.get<string[]>('/mandis/states');
        return response.data;
    },

    /**
     * Get districts by state
     */
    async getDistrictsByState(state: string): Promise<string[]> {
        const response = await api.get<string[]>(`/mandis/districts?state=${encodeURIComponent(state)}`);
        return response.data;
    },

    /**
     * Get mandis with advanced filtering and distance calculation
     */
    async getWithFilters(filters: MandiFilters = {}): Promise<MandisWithFiltersResponse> {
        const params = new URLSearchParams();

        if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
        if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
        if (filters.search) params.append('search', filters.search);
        if (filters.states?.length) params.append('states', filters.states.join(','));
        if (filters.district) params.append('district', filters.district);
        if (filters.commodity) params.append('commodity', filters.commodity);
        if (filters.maxDistanceKm !== undefined) params.append('max_distance_km', filters.maxDistanceKm.toString());
        if (filters.userLat !== undefined) params.append('user_lat', filters.userLat.toString());
        if (filters.userLon !== undefined) params.append('user_lon', filters.userLon.toString());
        if (filters.userDistrict) params.append('user_district', filters.userDistrict);
        if (filters.userState) params.append('user_state', filters.userState);
        if (filters.hasFacility) params.append('has_facility', filters.hasFacility);
        if (filters.minRating !== undefined) params.append('min_rating', filters.minRating.toString());
        if (filters.sortBy) params.append('sort_by', filters.sortBy);
        if (filters.sortOrder) params.append('sort_order', filters.sortOrder);

        const queryString = params.toString();
        const url = queryString ? `/mandis/with-filters?${queryString}` : '/mandis/with-filters';

        const response = await api.get<MandisWithFiltersResponse>(url);
        return response.data;
    },

    /**
     * Get detailed mandi information
     */
    async getDetails(mandiId: string, userDistrict?: string | null, userState?: string | null): Promise<MandiDetail> {
        const params = new URLSearchParams();
        if (userDistrict) params.append('user_district', userDistrict);
        if (userState) params.append('user_state', userState);

        const queryString = params.toString();
        const url = queryString
            ? `/mandis/${mandiId}/details?${queryString}`
            : `/mandis/${mandiId}/details`;

        const response = await api.get<MandiDetail>(url);
        return response.data;
    },

    /**
     * Compare multiple mandis
     */
    async compare(
        mandiIds: string[],
        userLat?: number,
        userLon?: number
    ): Promise<{ mandis: MandiDetail[]; comparison_date: string }> {
        const params = new URLSearchParams();
        if (userLat !== undefined) params.append('user_lat', userLat.toString());
        if (userLon !== undefined) params.append('user_lon', userLon.toString());

        const queryString = params.toString();
        const url = queryString ? `/mandis/compare?${queryString}` : '/mandis/compare';

        const response = await api.post<{ mandis: MandiDetail[]; comparison_date: string }>(
            url,
            mandiIds
        );
        return response.data;
    },

    /**
     * Get a single mandi by ID
     */
    async getById(id: string): Promise<Mandi> {
        const response = await api.get<Mandi>(`/mandis/${id}`);
        return response.data;
    },

    /**
     * Search mandis by name or market code
     */
    async search(query: string, limit: number = 10): Promise<Mandi[]> {
        const response = await api.get<Mandi[]>(
            `/mandis/search/?q=${encodeURIComponent(query)}&limit=${limit}`
        );
        return response.data;
    },

    /**
     * Get user's location (browser geolocation)
     */
    getUserLocation(): Promise<{ lat: number; lon: number }> {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                    });
                },
                (error) => reject(error),
                { timeout: 10000 }
            );
        });
    },

    /**
     * Get current commodity prices for a mandi
     */
    async getCurrentPrices(mandiId: string, commodity?: string): Promise<any[]> {
        const url = commodity 
            ? `/mandis/${mandiId}/prices?commodity=${encodeURIComponent(commodity)}`
            : `/mandis/${mandiId}/prices`;
        const response = await api.get<any[]>(url);
        return response.data;
    },

    /**
     * Get nearby mandis based on user location
     */
    async getNearbyMandis(lat: number, lon: number, radiusKm: number = 50): Promise<any[]> {
        const response = await api.get<any[]>(
            `/mandis/nearby?lat=${lat}&lon=${lon}&radius_km=${radiusKm}`
        );
        return response.data;
    },

    /**
     * Calculate distance between two geographic points using Haversine formula
     */
    calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
        const R = 6371; // Earth's radius in kilometers
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;
        return Math.round(distance * 10) / 10; // Round to 1 decimal
    },
};
