import { apiWithLongTimeout } from "@/lib/api";

export interface ForecastPoint {
    date: string;
    predicted_price: number;
    confidence: "HIGH" | "MEDIUM" | "LOW";
    confidence_percent: number;
    lower_bound: number;
    upper_bound: number;
    recommendation: "SELL" | "HOLD" | "WAIT";
}

export interface ForecastSummary {
    trend: "INCREASING" | "DECREASING" | "STABLE";
    peak_date: string;
    peak_price: number;
    best_sell_window: [string, string];
}

export interface ForecastResponse {
    commodity: string;
    current_price: number;
    forecasts: ForecastPoint[];
    summary: ForecastSummary;
}

export const forecastsService = {
    async getForecasts(commodity: string, days: number): Promise<ForecastResponse> {
        const response = await apiWithLongTimeout.get('/forecasts', { params: { commodity, days } });
        return response.data;
    }
};
