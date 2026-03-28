/**
 * Soil Advisor API service layer.
 *
 * Provides typed functions for all 4 soil-advisor endpoints:
 * - getStates()         — list of 21 covered state names
 * - getDistricts(state) — districts with soil data for a state
 * - getBlocks(state, district) — blocks with soil data for a district
 * - getProfile(state, district, block) — full soil advisor response
 */
import api from '@/lib/api';

// ---------------------------------------------------------------------------
// Types (mirror the Pydantic schemas in backend/app/soil_advisor/schemas.py)
// ---------------------------------------------------------------------------

export interface NutrientDistribution {
  nutrient: string;
  high_pct: number;
  medium_pct: number;
  low_pct: number;
}

export interface CropRecommendation {
  crop_name: string;
  suitability_score: number;
  suitability_rank: number;
  seasonal_demand: 'HIGH' | 'MEDIUM' | 'LOW' | null;
}

export interface FertiliserAdvice {
  nutrient: string;
  low_pct: number;
  message: string;
  fertiliser_recommendation: string;
}

export interface SoilAdvisorResponse {
  state: string;
  district: string;
  block: string;
  cycle: string;
  disclaimer: string;
  nutrient_distributions: NutrientDistribution[];
  crop_recommendations: CropRecommendation[];
  fertiliser_advice: FertiliserAdvice[];
  coverage_gap: boolean;
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const soilAdvisorApi = {
  /**
   * Return the 21 state names covered by the ICAR dataset.
   */
  getStates: (): Promise<string[]> =>
    api.get<string[]>('/soil-advisor/states').then((r) => r.data),

  /**
   * Return districts with soil data for the given state.
   */
  getDistricts: (state: string): Promise<string[]> =>
    api
      .get<string[]>('/soil-advisor/districts', { params: { state } })
      .then((r) => r.data),

  /**
   * Return blocks with soil data for the given state + district.
   */
  getBlocks: (state: string, district: string): Promise<string[]> =>
    api
      .get<string[]>('/soil-advisor/blocks', { params: { state, district } })
      .then((r) => r.data),

  /**
   * Return the full soil advisor profile for a block.
   */
  getProfile: (
    state: string,
    district: string,
    block: string
  ): Promise<SoilAdvisorResponse> =>
    api
      .get<SoilAdvisorResponse>('/soil-advisor/profile', {
        params: { state, district, block },
      })
      .then((r) => r.data),
};
