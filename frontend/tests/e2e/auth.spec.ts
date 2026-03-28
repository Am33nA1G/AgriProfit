import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Shared mock helpers
// ---------------------------------------------------------------------------

/** Mock the request-otp endpoint to succeed. */
async function mockRequestOtp(page: any) {
  await page.route('**/api/v1/auth/request-otp', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'OTP sent successfully' }),
    });
  });
}

/** Mock verify-otp to return an existing (non-new) user. */
async function mockVerifyOtpExisting(page: any) {
  await page.route('**/api/v1/auth/verify-otp', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-jwt-token',
        token_type: 'bearer',
        is_new_user: false,
      }),
    });
  });
}

/** Mock /auth/me to return a complete profile. */
async function mockGetMe(page: any) {
  await page.route('**/api/v1/auth/me', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-123',
        phone_number: '+919876543210',
        name: 'Test Farmer',
        role: 'farmer',
        is_profile_complete: true,
        language: 'en',
        is_active: true,
      }),
    });
  });
}

// ---------------------------------------------------------------------------
// Test 1: Phone step renders correctly
// ---------------------------------------------------------------------------
test('Auth 1: phone step renders with Send OTP button disabled for empty input', async ({ page }) => {
  await page.goto('/login');
  await page.waitForSelector('#phone', { state: 'visible' });

  // Phone input is present and empty
  await expect(page.locator('#phone')).toBeVisible();
  await expect(page.locator('#phone')).toHaveValue('');

  // Send OTP button disabled (phoneNumber.length < 10)
  const sendBtn = page.locator('button[type="submit"]');
  await expect(sendBtn).toBeDisabled();

  // Register link present
  await expect(page.getByRole('link', { name: /Create Free Account/i })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 2: Phone validation rejects bad numbers
// ---------------------------------------------------------------------------
test('Auth 2: invalid phone number shows validation error', async ({ page }) => {
  await page.goto('/login');
  await page.waitForSelector('#phone', { state: 'visible' });

  // Enter a number that starts with 1 (invalid — must start with 6-9)
  await page.fill('#phone', '1234567890');
  // Trigger blur to fire validation
  await page.locator('#phone').blur();

  // Error message should appear
  await expect(page.locator('#phone-error')).toBeVisible();
  await expect(page.locator('#phone-error')).toContainText('Must start with 6-9');
});

// ---------------------------------------------------------------------------
// Test 3: Happy path — request OTP → OTP step appears
// ---------------------------------------------------------------------------
test('Auth 3: valid phone number sends OTP and shows OTP step', async ({ page }) => {
  await mockRequestOtp(page);

  await page.goto('/login');
  await page.waitForSelector('#phone', { state: 'visible' });

  // Enter valid phone (starts with 9, 10 digits)
  await page.fill('#phone', '9876543210');

  // Send OTP button should be enabled
  const sendBtn = page.locator('button[type="submit"]');
  await expect(sendBtn).toBeEnabled();
  await sendBtn.click();

  // OTP step: success banner appears with phone number
  await page.waitForSelector('#otp', { state: 'visible' });
  await expect(page.getByText('OTP sent successfully!')).toBeVisible();
  await expect(page.getByText('+91 9876543210')).toBeVisible();

  // OTP input is auto-focused and empty
  await expect(page.locator('#otp')).toHaveValue('');

  // Verify & Login button disabled until 6 digits entered
  await expect(page.locator('button[type="submit"]')).toBeDisabled();
});

// ---------------------------------------------------------------------------
// Test 4: Full login happy path → redirected to /dashboard
// ---------------------------------------------------------------------------
test('Auth 4: correct OTP verifies and redirects to dashboard', async ({ page }) => {
  await mockRequestOtp(page);
  await mockVerifyOtpExisting(page);
  await mockGetMe(page);

  await page.goto('/login');
  await page.waitForSelector('#phone', { state: 'visible' });

  // Step 1: enter phone
  await page.fill('#phone', '9876543210');
  await page.locator('button[type="submit"]').click();

  // Step 2: enter OTP
  await page.waitForSelector('#otp', { state: 'visible' });
  await page.fill('#otp', '123456');

  // Verify & Login button should now be enabled
  const verifyBtn = page.locator('button[type="submit"]');
  await expect(verifyBtn).toBeEnabled();
  await verifyBtn.click();

  // Should redirect to /dashboard
  await page.waitForURL('**/dashboard', { timeout: 10_000 });
  expect(page.url()).toContain('/dashboard');
});

// ---------------------------------------------------------------------------
// Test 5: Wrong OTP shows error and stays on OTP step
// ---------------------------------------------------------------------------
test('Auth 5: wrong OTP shows error message without redirecting', async ({ page }) => {
  await mockRequestOtp(page);

  // Mock verify-otp to return 400 invalid OTP
  await page.route('**/api/v1/auth/verify-otp', async (route: any) => {
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Invalid OTP. Please try again.' }),
    });
  });

  await page.goto('/login');
  await page.fill('#phone', '9876543210');
  await page.locator('button[type="submit"]').click();

  await page.waitForSelector('#otp', { state: 'visible' });
  await page.fill('#otp', '000000');
  await page.locator('button[type="submit"]').click();

  // Error message appears
  await expect(page.locator('#otp-error')).toBeVisible();
  await expect(page.locator('#otp-error')).toContainText('Invalid OTP');

  // Still on OTP step — OTP input still visible
  await expect(page.locator('#otp')).toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 6: "Change number" button goes back to phone step
// ---------------------------------------------------------------------------
test('Auth 6: Change number button returns to phone step and clears OTP', async ({ page }) => {
  await mockRequestOtp(page);

  await page.goto('/login');
  await page.fill('#phone', '9876543210');
  await page.locator('button[type="submit"]').click();

  await page.waitForSelector('#otp', { state: 'visible' });
  await page.fill('#otp', '123456');

  // Click "Change number"
  await page.getByRole('button', { name: /Change number/i }).click();

  // Back on phone step — phone input visible, OTP input gone
  await expect(page.locator('#phone')).toBeVisible();
  await expect(page.locator('#otp')).not.toBeVisible();
});

// ---------------------------------------------------------------------------
// Test 7: New user redirected to /register
// ---------------------------------------------------------------------------
test('Auth 7: new user is redirected to register after OTP verification', async ({ page }) => {
  await mockRequestOtp(page);

  await page.route('**/api/v1/auth/verify-otp', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-jwt-new-user',
        token_type: 'bearer',
        is_new_user: true,
      }),
    });
  });

  await page.goto('/login');
  await page.fill('#phone', '9876543210');
  await page.locator('button[type="submit"]').click();

  await page.waitForSelector('#otp', { state: 'visible' });
  await page.fill('#otp', '123456');
  await page.locator('button[type="submit"]').click();

  // Should redirect to /register
  await page.waitForURL('**/register**', { timeout: 10_000 });
  expect(page.url()).toContain('/register');
});
