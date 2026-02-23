# AgriProfit Mobile

## What This Is

AgriProfit Mobile is a React Native + Expo app that brings the full AgriProfit experience to mobile devices. The web app (Next.js + Tailwind) is the source of truth for design and functionality — this project achieves complete parity with it. The app serves farmers, analysts, and traders who need agricultural commodity price data on mobile.

## Core Value

Farmers and traders get the same accurate, real-time market price data on mobile that they get on web — with the same design quality and feature set.

## Requirements

### Validated

<!-- Web app capabilities already proven — these exist and work on web. -->

- ✓ OTP-based phone number authentication — existing (web + backend)
- ✓ JWT session management with 24h expiry — existing (web + backend)
- ✓ Commodity price data display with historical trends — existing (web + backend)
- ✓ Market/mandi search and filtering — existing (web)
- ✓ Price trend charts and data visualization — existing (web, recharts)
- ✓ Data sync from data.gov.in (background, APScheduler) — existing (backend)
- ✓ Role-based access (user / admin) — existing (backend)
- ✓ Rate-limited API with Redis fallback — existing (backend)

### Active

<!-- Mobile parity goals — building toward these. -->

- [ ] Mobile design system matches web (colors, typography, spacing, component style)
- [ ] Auth flow (OTP request + verify) functional and styled
- [ ] Price charts rendered on mobile (native charting library)
- [ ] Commodity/market search with filter UI
- [ ] Navigation structure matches web information architecture
- [ ] All authenticated routes protected and session-aware
- [ ] Production-ready error handling and loading states
- [ ] API client configured for mobile (baseURL, auth headers, interceptors)

### Out of Scope

- New features not in web app — this is parity, not expansion
- Web app redesign — mobile follows web, not the other way
- Backend API changes — mobile consumes existing endpoints unchanged
- Admin panel on mobile — web-only feature
- Offline mode / local data caching beyond React Query defaults

## Context

**Existing web app:** Next.js 15, React 19, Tailwind CSS 4. Uses Radix UI primitives, lucide-react icons, recharts for charts, TanStack React Query for server state, zustand for client state, sonner for toasts.

**Mobile stack:** React Native 0.74, Expo 51. Mobile folder exists with partial screens. Design system not yet applied — biggest visible gap.

**Backend:** FastAPI at `/api/v1`, OTP auth via phone number, all price/commodity data via REST. No backend changes required.

**Mobile-specific gaps identified:** Price charts, search/filter UX, navigation routing, auth flows, design system application.

**Authentication:** OTP-only (no password). Phone → OTP → JWT stored in SecureStore/AsyncStorage.

## Constraints

- **Tech Stack**: React Native + Expo — no Expo ejection unless absolutely necessary
- **Backend Compatibility**: Consume existing FastAPI endpoints as-is; no schema changes
- **Design Source**: Web app is design truth — extract and mirror, do not redesign
- **Scope**: No new features; parity only
- **Commits**: Atomic — one concern per commit

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React Native + Expo (keep as-is) | Already chosen; ejection would bloat scope | — Pending |
| Mirror web design system | Consistency across platforms; no new design needed | — Pending |
| Consume backend unchanged | Backend is stable and well-tested; mobile must adapt | — Pending |
| Mobile-native charting (not recharts) | recharts is DOM-based; need RN-compatible chart lib | — Pending |

---
*Last updated: 2026-02-23 after initialization*
