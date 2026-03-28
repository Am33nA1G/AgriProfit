import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const FULL_FORECAST = {
  commodity: 'wheat',
  district: 'Pune',
  horizon_days: 7,
  direction: 'up',
  price_low: 1800.0,
  price_mid: 2000.0,
  price_high: 2200.0,
  confidence_colour: 'Green',
  tier_label: 'full model',
  last_data_date: '2025-10-30',
  r2_score: 0.65,
  coverage_message: null,
  data_freshness_days: 2,
  is_stale: false,
  n_markets: 10,
  typical_error_inr: null,
  mape_pct: 8.5,
  model_version: 'v5',
  forecast_points: [
    { date: '2025-10-31', price_low: 1810, price_mid: 2010, price_high: 2210 },
    { date: '2025-11-01', price_low: 1820, price_mid: 2020, price_high: 2220 },
    { date: '2025-11-02', price_low: 1830, price_mid: 2030, price_high: 2230 },
    { date: '2025-11-03', price_low: 1840, price_mid: 2040, price_high: 2240 },
    { date: '2025-11-04', price_low: 1850, price_mid: 2050, price_high: 2250 },
    { date: '2025-11-05', price_low: 1860, price_mid: 2060, price_high: 2260 },
    { date: '2025-11-06', price_low: 1870, price_mid: 2070, price_high: 2270 },
  ],
};

const FALLBACK_FORECAST = {
  commodity: 'jute',
  district: 'Bellary',
  horizon_days: 7,
  direction: 'flat',
  price_low: null,
  price_mid: null,
  price_high: null,
  confidence_colour: 'Yellow',
  tier_label: 'seasonal average fallback',
  last_data_date: '2025-06-15',
  r2_score: null,
  coverage_message: 'Insufficient price history for Bellary. Showing seasonal averages.',
  data_freshness_days: 0,
  is_stale: false,
  n_markets: 0,
  typical_error_inr: null,
  mape_pct: null,
  model_version: null,
  forecast_points: [],
};

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/**
 * Register all four forecast API mocks in the correct order:
 * commodities → states → districts → actual forecast.
 * More-specific routes are registered first so Playwright matches them before
 * the broader wildcard.
 */
async function setupMocks(
  page: Page,
  options: {
    commodities?: string[];
    forecastBody?: object;
    trackRequests?: string[];
  } = {}
) {
  const commodities = options.commodities ?? ['wheat', 'rice', 'jute', 'tomato', 'potato'];
  const forecastBody = options.forecastBody ?? FULL_FORECAST;

  // Playwright evaluates routes in LIFO order (last registered = first checked).
  // Register broad/overlapping patterns first so specific ones take priority.

  // 1. Actual forecast — registered first (lowest priority, caught last)
  //    Pattern: /forecast/{commodity}/{district} — 2 path segments after /forecast/
  if (options.trackRequests) {
    await page.route('**/api/v1/forecast/*/*', async (route) => {
      const url = route.request().url();
      // Only track real forecast requests, not states/districts/commodities
      if (!url.includes('/states/') && !url.includes('/districts/') && !url.includes('/commodities')) {
        options.trackRequests!.push(url);
      }
      await route.abort();
    });
  } else {
    await page.route('**/api/v1/forecast/*/*', async (route) => {
      const url = route.request().url();
      if (url.includes('/states/') || url.includes('/districts/')) {
        // Should not reach here after specific handlers are registered, but continue safely
        await route.continue();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(forecastBody),
      });
    });
  }

  // 2. Districts — registered second (medium priority)
  await page.route('**/api/v1/forecast/districts/**', async (route) => {
    const url = route.request().url();
    const districts = url.includes('/Maharashtra')
      ? ['Pune', 'Nashik']
      : ['Bellary', 'Bangalore'];
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(districts),
    });
  });

  // 3. States — registered third (takes priority over /*/*)
  await page.route('**/api/v1/forecast/states/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(['Maharashtra', 'Karnataka']),
    });
  });

  // 4. Commodity list — registered last (highest priority, checked first)
  await page.route('**/api/v1/forecast/commodities', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(commodities),
    });
  });
}

/**
 * Navigate to /forecast and wait for commodity options to load.
 */
async function gotoForecastPage(page: Page): Promise<void> {
  await page.goto('/forecast');
  await page.waitForSelector('#commodity-select', { state: 'visible' });
  await page.waitForSelector('#commodity-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 10_000,
  });
}

/**
 * Full cascade select: commodity → state → district.
 * Waits for each dependent dropdown to become enabled after the prior select.
 */
async function selectCommodityStateDistrict(
  page: Page,
  commodity: string,
  state: string,
  district: string
): Promise<void> {
  await page.selectOption('#commodity-select', commodity);
  // State select is disabled until states API resolves
  await page.waitForSelector('#state-select:not([disabled])', { timeout: 5_000 });
  await page.waitForSelector('#state-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 5_000,
  });
  await page.selectOption('#state-select', state);
  // District select is disabled until districts API resolves
  await page.waitForSelector('#district-select:not([disabled])', { timeout: 5_000 });
  await page.waitForSelector('#district-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 5_000,
  });
  await page.selectOption('#district-select', district);
}

// ---------------------------------------------------------------------------
// Gap 1: Forecast Page Visual Rendering
// Verify direction label, confidence label, model label, price range, chart,
// data freshness, and no fallback banner for a full-model response.
// ---------------------------------------------------------------------------
test('Gap 1: forecast page renders correctly for full model response (Wheat + Pune)', async ({ page }) => {
  await setupMocks(page, { forecastBody: FULL_FORECAST });
  await gotoForecastPage(page);

  await selectCommodityStateDistrict(page, 'wheat', 'Maharashtra', 'Pune');

  // Wait for forecast result to appear
  await page.waitForSelector('#forecast-result', { state: 'visible', timeout: 10_000 });

  // 1. Direction label: direction=up → "RISING"
  await expect(page.locator('#forecast-result')).toContainText('RISING');

  // 2. Confidence label: Green → "Reliable"
  await expect(page.locator('#forecast-result')).toContainText('Reliable');

  // 3. Model version: model_version=v5 → "v5 · LightGBM"
  await expect(page.locator('#forecast-result')).toContainText('v5 · LightGBM');

  // 4. Fallback banner must NOT be present for full model response
  await expect(page.locator('#fallback-banner')).not.toBeVisible();

  // 5. Data freshness note contains the last_data_date value
  await expect(page.locator('#data-freshness')).toBeVisible();
  await expect(page.locator('#data-freshness')).toContainText('2025-10-30');

  // 6. Price range: price_mid=2000.0 → "₹2000.00"
  await expect(page.locator('#forecast-result')).toContainText('₹2000.00');

  // 7. Price range heading
  await expect(page.locator('#forecast-result')).toContainText('Predicted Price Range');

  // 8. Forecast chart visible (forecast_points.length > 0 and confidence !== 'Red')
  await expect(page.locator('#forecast-chart')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Gap 2: Seasonal Fallback Banner
// Verify the "Limited Data Coverage" banner renders when tier_label is
// "seasonal average fallback", and the chart / price range are hidden.
// ---------------------------------------------------------------------------
test('Gap 2: seasonal fallback banner renders for low-coverage district', async ({ page }) => {
  await setupMocks(page, {
    commodities: ['jute', 'wheat', 'rice'],
    forecastBody: FALLBACK_FORECAST,
  });
  await gotoForecastPage(page);

  await selectCommodityStateDistrict(page, 'jute', 'Karnataka', 'Bellary');

  // Wait for forecast result
  await page.waitForSelector('#forecast-result', { state: 'visible', timeout: 10_000 });

  // 1. Fallback banner visible
  await expect(page.locator('#fallback-banner')).toBeVisible();

  // 2. Banner heading
  await expect(page.locator('#fallback-banner')).toContainText('Limited Data Coverage');

  // 3. Banner contains coverage_message
  await expect(page.locator('#fallback-banner')).toContainText('Insufficient price history for Bellary');

  // 4. Direction label: direction=flat → "STABLE"
  await expect(page.locator('#forecast-result')).toContainText('STABLE');

  // 5. Confidence label: Yellow → "Directional only"
  await expect(page.locator('#forecast-result')).toContainText('Directional only');

  // 6. Price range card NOT rendered (price_mid is null → PriceRangeBar returns null)
  await expect(page.locator('text=Predicted Price Range')).not.toBeVisible();

  // 7. Chart NOT rendered (forecast_points is empty)
  await expect(page.locator('#forecast-chart')).not.toBeVisible();

  // 8. Data freshness still shows last_data_date
  await expect(page.locator('#data-freshness')).toBeVisible();
  await expect(page.locator('#data-freshness')).toContainText('2025-06-15');
});

// ---------------------------------------------------------------------------
// Gap 3: Cascading Select Reset
// Verify changing state clears the district dropdown and does not fire a
// stale forecast request for the previous district.
// ---------------------------------------------------------------------------
test('Gap 3: changing state clears district and does not fire stale forecast query', async ({ page }) => {
  const forecastRequests: string[] = [];
  await setupMocks(page, { trackRequests: forecastRequests });
  await gotoForecastPage(page);

  // Step 1: full cascade select → wheat + Maharashtra + Pune
  await selectCommodityStateDistrict(page, 'wheat', 'Maharashtra', 'Pune');

  // At least one forecast request for wheat/Pune should have fired
  await page.waitForTimeout(500);
  expect(forecastRequests.some((url) => url.includes('Pune'))).toBe(true);

  // Step 2: change state — should reset district and suppress forecast query
  forecastRequests.length = 0;
  await page.selectOption('#state-select', 'Karnataka');

  await page.waitForTimeout(500);

  // 3. District value resets to empty string
  expect(await page.inputValue('#district-select')).toBe('');

  // 4. No forecast fired (district is now empty → canFetch=false)
  expect(forecastRequests.length).toBe(0);

  // 5. Empty state panel visible (canFetch is false)
  await expect(page.locator('#forecast-empty')).toBeVisible();

  // 6. After Karnataka's districts load, they appear (not Maharashtra's)
  await page.waitForSelector('#district-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 5_000,
  });
  const districtOptions = await page.locator('#district-select option').allTextContents();
  expect(districtOptions).toContain('Bellary');
  expect(districtOptions).toContain('Bangalore');
  expect(districtOptions).not.toContain('Pune');
});
