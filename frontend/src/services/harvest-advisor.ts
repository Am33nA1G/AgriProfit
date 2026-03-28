import api from '@/lib/api';

export interface WeatherWarning {
  warning_type: 'drought' | 'flood' | 'heat_stress' | 'cold_stress' | 'excess_rain';
  severity: 'low' | 'medium' | 'high' | 'extreme';
  message: string;
  source: 'historical' | 'forecast' | 'both';
  affected_period: string;
  crop_impact: string;
}

export interface CropRecommendation {
  crop_name: string;
  rank: number;
  gross_revenue_per_ha: number;
  input_cost_per_ha: number;
  expected_profit_per_ha: number;
  expected_yield_kg_ha: number;
  expected_price_per_quintal: number;
  yield_confidence: 'high' | 'medium' | 'low';
  price_direction: 'up' | 'flat' | 'down';
  price_confidence_colour: 'Green' | 'Yellow' | 'Red';
  sowing_window: string;
  harvest_window: string;
  soil_suitability_note?: string | null;
}

export interface HarvestAdvisorResponse {
  state: string;
  district: string;
  season: string;
  recommendations: CropRecommendation[];
  weather_warnings: WeatherWarning[];
  rainfall_deficit_pct?: number | null;
  drought_risk?: string | null;
  soil_data_available: boolean;
  yield_data_available: boolean;
  forecast_available: boolean;
  disclaimer: string;
  generated_at: string;
  coverage_notes: string[];
}

export async function getRecommendation(
  state: string,
  district: string,
  season: string
): Promise<HarvestAdvisorResponse | null> {
  try {
    const response = await api.get<HarvestAdvisorResponse>('/harvest-advisor/recommend', {
      params: { state, district, season },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch harvest recommendation:', error);
    return null;
  }
}

export async function getWeatherWarnings(
  state: string,
  district: string
): Promise<WeatherWarning[]> {
  try {
    const response = await api.get<WeatherWarning[]>('/harvest-advisor/weather-warnings', {
      params: { state, district },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch weather warnings:', error);
    return [];
  }
}

export async function getHarvestAdvisorDistricts(state: string): Promise<string[]> {
  try {
    const response = await api.get<string[]>('/harvest-advisor/districts', {
      params: { state },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch districts:', error);
    return [];
  }
}
