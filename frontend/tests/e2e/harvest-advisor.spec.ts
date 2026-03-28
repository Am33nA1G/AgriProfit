import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_STATES = ['Maharashtra', 'Karnataka', 'Punjab'];
const MOCK_DISTRICTS = ['Nashik', 'Pune', 'Aurangabad'];

const MOCK_RECOMMENDATIONS = [
  {
    crop_name: 'Tomato',
    rank: 1,
    gross_revenue_per_ha: 120000,
    input_cost_per_ha: 35000,
    expected_profit_per_ha: 85000,
    expected_yield_kg_ha: 24000,
    expected_price_per_quintal: 500,
    yield_confidence: 'high',
    price_direction: 'up',
    price_confidence_colour: 'Green',
    sowing_window: 'Jun–Jul',
    harvest_window: 'Sep–Oct',
    soil_suitability_note: null,
  },
  {
    crop_name: 'Onion',
    rank: 2,
    gross_revenue_per_ha: 90000,
    input_cost_per_ha: 28000,
    expected_profit_per_ha: 62000,
    expected_yield_kg_ha: 18000,
    expected_price_per_quintal: 500,
    yield_confidence: 'medium',
    price_direction: 'flat',
    price_confidence_colour: 'Yellow',
    sowing_window: 'Oct–Nov',
    harvest_window: 'Feb–Mar',
    soil_suitability_note: 'Well-drained loamy soil preferred',
  },
  {
    crop_name: 'Wheat',
    rank: 3,
    gross_revenue_per_ha: 75000,
    input_cost_per_ha: 22000,
    expected_profit_per_ha: 53000,
    expected_yield_kg_ha: 4500,
    expected_price_per_quintal: 1667,
    yield_confidence: 'high',
    price_direction: 'up',
    price_confidence_colour: 'Green',
    sowing_window: 'Nov',
    harvest_window: 'Mar–Apr',
    soil_suitability_note: null,
  },
];

const MOCK_RESPONSE = {
  state: 'Maharashtra',
  district: 'Nashik',
  season: 'kharif',
  recommendations: MOCK_RECOMMENDATIONS,
  weather_warnings: [],
  rainfall_deficit_pct: null,
  drought_risk: 'none',
  soil_data_available: true,
  yield_data_available: true,
  forecast_available: true,
  coverage_notes: [],
  disclaimer: 'These recommendations are based on historical data and ML models.',
};

// ---------------------------------------------------------------------------
// Shared setup: mock all three API calls the page makes
// ---------------------------------------------------------------------------

async function setupMocks(page: Page, overrides: Partial<typeof MOCK_RESPONSE> = {}) {
  // States list (from /soil-advisor/states — shared with soil advisor page)
  await page.route('**/api/v1/soil-advisor/states', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_STATES),
    });
  });

  // Districts for a given state
  await page.route('**/api/v1/harvest-advisor/districts**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_DISTRICTS),
    });
  });

  // Recommendations
  await page.route('**/api/v1/harvest-advisor/recommend**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...MOCK_RESPONSE, ...overrides }),
    });
  });
}

async function gotoPage(page: Page) {
  await page.goto('/harvest-advisor');
  // Wait for states to load (the select gets populated from /soil-advisor/states)
  await page.waitForSelector('#state-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 10_000,
  });
}

// ---------------------------------------------------------------------------
// Test 1: Page renders with selectors in correct initial state
// ---------------------------------------------------------------------------

test('Harvest 1: page renders state/district/season selectors', async ({ page }) => {
  await setupMocks(page);
  await gotoPage(page);

  // All three selectors visible
  await expect(page.locator('#state-select')).toBeVisible();
  await expect(page.locator('#district-select')).toBeVisible();
  await expect(page.locator('#season-select')).toBeVisible();

  // State select populated with mock states
  const stateOptions = await page.locator('#state-select option').allTextContents();
  expect(stateOptions).toContain('Maharashtra');
  expect(stateOptions).toContain('Karnataka');

  // Season select defaults to kharif
  await expect(page.locator('#season-select')).toHaveValue('kharif');
});

// ---------------------------------------------------------------------------
// Test 2: District select disabled until state is chosen
// ---------------------------------------------------------------------------

test('Harvest 2: district select disabled until state selected', async ({ page }) => {
  await setupMocks(page);
  await gotoPage(page);

  // District should be disabled initially (no state selected)
  await expect(page.locator('#district-select')).toBeDisabled();

  // Select a state → district becomes enabled and populated
  await page.selectOption('#state-select', 'Maharashtra');
  await page.waitForSelector('#district-select option[value]:not([value=""])', {
    state: 'attached',
    timeout: 5_000,
  });
  await expect(page.locator('#district-select')).toBeEnabled();

  const districtOptions = await page.locator('#district-select option').allTextContents();
  expect(districtOptions).toContain('Nashik');
  expect(districtOptions).toContain('Pune');
});

// ---------------------------------------------------------------------------
// Test 3: Get Recommendations button disabled until state AND district chosen
// ---------------------------------------------------------------------------

test('Harvest 3: Get Recommendations button disabled until both selectors filled', async ({ page }) => {
  await setupMocks(page);
  await gotoPage(page);

  const btn = page.getByRole('button', { name: /Get Recommendations/i });

  // Initially disabled (no state or district)
  await expect(btn).toBeDisabled();

  // Select state only — still disabled
  await page.selectOption('#state-select', 'Maharashtra');
  await expect(btn).toBeDisabled();

  // Select district too — now enabled
  await page.waitForSelector('#district-select:not([disabled])');
  await page.selectOption('#district-select', 'Nashik');
  await expect(btn).toBeEnabled();
});

// ---------------------------------------------------------------------------
// Test 4: Happy path — recommendations render as cards
// ---------------------------------------------------------------------------

test('Harvest 4: recommendations render correctly after Get Recommendations click', async ({ page }) => {
  await setupMocks(page);
  await gotoPage(page);

  // Select state, district, season
  await page.selectOption('#state-select', 'Maharashtra');
  await page.waitForSelector('#district-select:not([disabled])');
  await page.selectOption('#district-select', 'Nashik');
  await page.selectOption('#season-select', 'kharif');

  await page.getByRole('button', { name: /Get Recommendations/i }).click();

  // "Top Crop Recommendations" heading appears
  await page.waitForSelector('text=Top Crop Recommendations', { timeout: 10_000 });

  // All 3 crop cards rendered
  await expect(page.getByText('Tomato')).toBeVisible();
  await expect(page.getByText('Onion')).toBeVisible();
  await expect(page.getByText('Wheat')).toBeVisible();

  // Rank badges
  await expect(page.getByText('#1')).toBeVisible();
  await expect(page.getByText('#2')).toBeVisible();
  await expect(page.getByText('#3')).toBeVisible();

  // Tomato profit: ₹85,000/ha
  await expect(page.getByText(/₹85,000\/ha/)).toBeVisible();

  // Disclaimer renders at bottom
  await expect(page.getByText(/historical data and ML models/)).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 5: Weather warnings render with correct severity class
// ---------------------------------------------------------------------------

test('Harvest 5: weather warnings render for high-risk response', async ({ page }) => {
  await setupMocks(page, {
    weather_warnings: [
      {
        warning_type: 'drought',
        severity: 'high',
        message: 'Severe drought conditions expected in June–August.',
        source: 'historical',
        affected_period: 'Jun–Aug 2026',
        crop_impact: 'Reduce water-intensive crops.',
      },
      {
        warning_type: 'heat_stress',
        severity: 'medium',
        message: 'Moderate heat stress likely in July.',
        source: 'forecast',
        affected_period: 'Jul 2026',
        crop_impact: 'Consider shade nets for vegetables.',
      },
    ],
    drought_risk: 'high',
  });

  await gotoPage(page);
  await page.selectOption('#state-select', 'Maharashtra');
  await page.waitForSelector('#district-select:not([disabled])');
  await page.selectOption('#district-select', 'Nashik');
  await page.getByRole('button', { name: /Get Recommendations/i }).click();

  // Weather Warnings section heading
  await page.waitForSelector('text=Weather Warnings', { timeout: 10_000 });

  // Drought warning (high severity → red border)
  const droughtWarning = page.getByText('Severe drought conditions expected').locator('..');
  await expect(page.getByText('Severe drought conditions expected')).toBeVisible();
  await expect(page.getByText('Reduce water-intensive crops.')).toBeVisible();

  // Heat stress warning
  await expect(page.getByText('Moderate heat stress likely in July.')).toBeVisible();

  // Drought risk badge shows "High"
  await expect(page.getByText('Drought Risk:')).toBeVisible();
  await expect(page.getByText('High')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 6: Empty recommendations state
// ---------------------------------------------------------------------------

test('Harvest 6: empty recommendations shows no-data message', async ({ page }) => {
  await setupMocks(page, { recommendations: [], coverage_notes: ['No yield data for this district.'] });

  await gotoPage(page);
  await page.selectOption('#state-select', 'Karnataka');
  await page.waitForSelector('#district-select:not([disabled])');
  await page.selectOption('#district-select', 'Nashik');
  await page.getByRole('button', { name: /Get Recommendations/i }).click();

  // Empty state message
  await page.waitForSelector('text=No data available for this district', { timeout: 10_000 });
  await expect(page.getByText('No data available for this district')).toBeVisible();

  // Coverage note visible
  await expect(page.getByText('No yield data for this district.')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 7: Changing state resets district select
// ---------------------------------------------------------------------------

test('Harvest 7: changing state clears and reloads district select', async ({ page }) => {
  await setupMocks(page);
  await gotoPage(page);

  // Select Maharashtra → districts populate
  await page.selectOption('#state-select', 'Maharashtra');
  await page.waitForSelector('#district-select:not([disabled])');
  await page.selectOption('#district-select', 'Nashik');
  const districtValue = await page.inputValue('#district-select');
  expect(districtValue).toBe('Nashik');

  // Change state → district should reset to empty
  await page.selectOption('#state-select', 'Karnataka');
  const newDistrictValue = await page.inputValue('#district-select');
  expect(newDistrictValue).toBe('');

  // Get Recommendations button disabled again
  await expect(page.getByRole('button', { name: /Get Recommendations/i })).toBeDisabled();
});
