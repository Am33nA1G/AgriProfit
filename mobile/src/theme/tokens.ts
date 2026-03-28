// mobile/src/theme/tokens.ts
// Single source of design truth for AgriProfit Mobile.
// ALL components must import from here — no raw hex or pixel values in components.
// Mirrors Tailwind CSS 4 variables from frontend/src/app/globals.css.

// ─── Colors ───────────────────────────────────────────────────────────────────

export const colors = {
    // Brand — green-600 primary (DESIGN-02, matches globals.css --color-primary: #166534)
    primary: '#16a34a',        // green-600 — buttons, links, active states
    primaryLight: '#dcfce7',   // green-100 — chip backgrounds, highlights
    primaryDark: '#166534',    // green-800 — pressed state

    // Surface
    background: '#ffffff',     // page background
    card: '#ffffff',           // card background (DESIGN-03)
    surface: '#f9fafb',        // secondary surface (gray-50)

    // Border — 1px card borders (DESIGN-03)
    border: '#e5e7eb',         // gray-200
    inputBorder: '#d1d5db',    // gray-300

    // Text
    foreground: '#111827',     // gray-900 — body text
    muted: '#6b7280',          // gray-500 — secondary text (DESIGN-07)
    mutedLight: '#9ca3af',     // gray-400 — placeholder text
    placeholder: '#9ca3af',

    // Status (DESIGN-07)
    success: '#16a34a',        // green-600 — gains, positive
    successLight: '#dcfce7',   // green-100
    error: '#dc2626',          // red-600 — losses, errors
    errorLight: '#fef2f2',     // red-50
    warning: '#d97706',        // amber-600
    warningLight: '#fffbeb',   // amber-50

    // UI states
    disabled: '#d1d5db',       // gray-300
    overlay: 'rgba(0,0,0,0.5)',
    transparent: 'transparent',

    // Chart palette
    chart1: '#e8611a',         // orange
    chart2: '#2d9d8f',         // teal
    chart3: '#3b5998',         // dark blue
    chart4: '#c8a400',         // gold
    chart5: '#c47800',         // amber
} as const;

// ─── Typography ───────────────────────────────────────────────────────────────

export const typography = {
    fontFamily: {
        sans: 'System',          // system default (SF Pro on iOS, Roboto on Android)
        mono: 'monospace',
    },
    fontSize: {
        xs: 12,
        sm: 14,
        base: 16,
        lg: 18,
        xl: 20,
        '2xl': 24,
        '3xl': 30,
    },
    fontWeight: {
        normal: '400' as const,
        medium: '500' as const,
        semibold: '600' as const,
        bold: '700' as const,
    },
    lineHeight: {
        tight: 1.25,
        normal: 1.5,
        relaxed: 1.75,
    },
} as const;

// ─── Spacing ──────────────────────────────────────────────────────────────────
// Base unit: 4px — matches web Tailwind p-1=4px, p-4=16px, gap-6=24px (DESIGN-05)

export const spacing = {
    0: 0,
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
    6: 24,
    8: 32,
    10: 40,
    12: 48,
    16: 64,
} as const;

// ─── Border Radii ─────────────────────────────────────────────────────────────

export const radii = {
    none: 0,
    sm: 4,
    md: 8,
    lg: 12,    // card radius — DESIGN-03: 12px border radius
    xl: 16,
    '2xl': 24,
    full: 9999,
} as const;

// ─── Shadows / Elevation ──────────────────────────────────────────────────────
// DESIGN-06: Cards use elevation:4 Android, shadow props iOS

export const shadows = {
    none: {
        shadowColor: 'transparent',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0,
        shadowRadius: 0,
        elevation: 0,
    },
    sm: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    card: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.08,
        shadowRadius: 4,
        elevation: 4,  // DESIGN-06
    },
    modal: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.15,
        shadowRadius: 16,
        elevation: 16,
    },
} as const;

// ─── Z-Index ──────────────────────────────────────────────────────────────────

export const zIndex = {
    base: 0,
    card: 1,
    dropdown: 10,
    modal: 100,
    toast: 200,
} as const;

// ─── Default export ───────────────────────────────────────────────────────────

const tokens = {
    colors,
    typography,
    spacing,
    radii,
    shadows,
    zIndex,
} as const;

export default tokens;
