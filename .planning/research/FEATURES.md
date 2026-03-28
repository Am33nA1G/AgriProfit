# Feature Landscape: Agricultural Market Intelligence — ML Layer

**Domain:** Agricultural price intelligence and crop advisory platform for Indian farmers
**Researched:** 2026-03-01
**Overall confidence:** MEDIUM — based on multiple credible sources (eNAM, ICAR, peer-reviewed agri-ML papers, GSMA field research, agmarknet platform analysis). No single source covers all four feature areas with equal depth.

---

## Context: What This Milestone Is Adding

The existing platform already handles: price data display, mandi search, transport logistics (freight, spoilage, risk). This research covers the four new ML-driven capabilities being added:

1. Price forecasting (7–30 day horizon)
2. Seasonal price calendar (best month to sell)
3. Crop recommendation (soil profile + market signals)
4. Mandi arbitrage dashboard (cross-mandi price differentials)

All conclusions are anchored to the **Indian smallholder farmer context**: low-to-medium digital literacy, district-level data granularity, feature phone and entry-level Android use, and commodity decision-making tied to planting/harvesting cycles.

---

## Table Stakes

Features farmers expect from an agricultural intelligence platform. Their absence makes the platform feel incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Current mandi price (today) | Every Indian agri app shows this; agmarknet, Kisan Suvidha, eNAM, IFFCO Kisan all lead with current price | Low | Already partially built; table stakes for any price context |
| Price trend direction (up/down vs yesterday/last week) | Farmers read trend, not absolute price. "Is it going up?" is the primary question | Low | Arrow + colour + percentage change is sufficient; no chart required |
| Nearest mandi results by default | AgriMarket uses GPS to show nearest 50km mandis automatically; farmers don't want to navigate | Low | Already in transport engine; surface it prominently |
| Seasonal best-month indicator for a commodity | Kisan Suvidha, agmarknet price trends, and IFFCO Kisan all provide seasonal price context; farmers use it to time storage decisions | Medium | 10-year monthly aggregation is pure stats, not ML |
| Coverage transparency | Soil Health Card scheme failure shows farmers distrust advice that doesn't explain its limitations | Low | Must show clearly: "This uses block-average soil data, not your specific field" |
| Local language / simple vocabulary | 94% farmer engagement with audio advice (Ama Krushi study); WhatsApp preferred over native apps; text must be simple | Low | Use Hindi numerals where appropriate; avoid technical jargon |

---

## Differentiators

Features that distinguish AgriProfit from government portals and generic advisory apps. Not universally expected, but create competitive advantage when done well.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 7-day price forecast with confidence indicator | Competing platforms (agmarknet, eNAM, Kisan Suvidha) show only current/historical prices — NO price forecasts. XGBoost/LSTM on 25M Agmarknet rows is genuinely novel | High | MAPE ~10–15% achievable for stable commodities; 14–17% for onion/tomato. Present as range, not point forecast |
| "Sell now vs wait" directional signal | Farmers' core question is a binary hold-or-sell decision, not a price number. A simple UP/DOWN/HOLD signal with a confidence colour is more actionable than a chart | Medium | Derived from forecast direction + confidence score. Avoids false precision |
| Seasonal sell window calendar with 10-year data | Government portals show daily prices, not aggregated seasonal patterns. A "historically, onion peaks in Oct–Nov in Maharashtra" calendar fills a genuine gap | Medium | Bar chart showing monthly average + interquartile range; call out the best 2-month window |
| Crop recommendation from soil deficit profile | SHC scheme provides soil health cards but has poor farmer adoption (only 49% follow recommendations). Translating NPK deficit + market price signal into a ranked crop shortlist solves a real gap | High | Only feasible at block level, not field level. Must communicate this limitation explicitly |
| Mandi arbitrage: net profit after transport | Most platforms show raw price differential. The existing transport logistics engine lets AgriProfit show NET profit after freight, spoilage, and time — a calculation no competitor does | High | Filter arbitrage alerts to those where net differential > transport break-even (~15–20% threshold) |
| Rainfall-adjusted price outlook | For onion, tomato, potato (TOP commodities): price spikes correlate with monsoon disruption. Showing "current season rainfall deficit = high price probability" is genuinely novel context | High | Requires district fuzzy matching to unlock; tiered: rainfall for 95% coverage, weather for 46% |
| Price confidence score by commodity | Academics note volatile commodities (CV > 0.6) have fundamentally unreliable short-term forecasts. Showing farmers "LOW confidence — onion prices highly unpredictable right now" is more honest and useful than a false precise forecast | Medium | Derived from recent CV%, data staleness, thin-market flags already in transport risk engine |

---

## Anti-Features

Features to explicitly NOT build. Either they mislead farmers, create distrust, or drain engineering time for zero farmer value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Precise rupee price forecasts displayed as fact | Academic research (MAPE 10–17% for volatile crops, up to 53% for ARIMA) shows forecasts have wide error bands. Showing "Onion will be ₹2,340/quintal on March 15" creates false precision and destroys trust when wrong | Show directional range: "Expected: ₹2,100–₹2,600 (moderate confidence)" |
| 30-day horizon forecasts for volatile crops | XGBoost and even LSTM lose predictive power beyond 7 days for onion/tomato/potato. Research shows model accuracy degrades sharply beyond 7–14 days for high-CV commodities | Cap at 7 days for volatile crops; show 30-day seasonal pattern (historical) instead of 30-day ML forecast |
| Yield prediction or production volume forecasts | Project scope explicitly excludes this (no area planted data, no harvest data). Even if built, it would mislead farmers | Out of scope; if asked, redirect to crop recommendation (what to grow) not yield (how much you'll get) |
| Individual field-level crop advice | Soil data is at block level (6,895 blocks across 31 states). Presenting block averages as field-specific advice is the same error that caused 59% of Soil Health Card non-adoption — samples not from each farmer's field | Always label: "Based on block-average soil data for [block name]. Your field may differ." |
| Crop price comparison tables with 20+ mandis | eNAM and agmarknet already provide raw multi-mandi tables. Farmers don't read tabular data well (low literacy context); the CEDA platform shows this is a researcher tool, not a farmer tool | Show top 3 mandis ranked by net profit, with a clear winner badge (as the transport breakdown already does) |
| Real-time live price streaming | API client exists but live wiring to ML model is out of scope. More importantly: agmarknet data arrives with 1–2 day lag. Displaying it as "real-time" misleads farmers | Show data freshness timestamp. "Prices as of yesterday" is honest and sufficient |
| Over-reliance on MSP as price floor | MSP is a political/procurement price that doesn't reflect mandi auction reality for most commodities. Including MSP as a "floor" in forecasts conflates policy with market | Keep MSP as a reference line only, not a forecast input or guarantee |
| Chatbot or conversational crop advisor in v1 | DeHaat and BharatAgri have invested years into NLP pipelines for regional languages; BharatAgri failed to raise bridge funding in 2025. The complexity-to-value ratio for v1 is unfavorable | Use structured menus and pre-computed recommendations instead of open-ended chat |
| Futures/derivatives integration | Out of farmer context. Indian smallholders are not using commodity futures. eNAM is digital auction, not futures | Irrelevant for this farmer segment |

---

## Feature Deep-Dives: What Each Feature Should Actually Do

### 1. Price Forecasting

**What horizon matters:** 7-day is the actionable horizon for harvest/sale decisions. 14-day for storage decisions. 30-day is only useful as a "seasonal direction" indicator, not a precise forecast.

**Accuracy expectations (MEDIUM confidence, from peer-reviewed 2024 literature):**
- Stable commodities (wheat, paddy, turmeric): MAPE 5–12% achievable with XGBoost
- Volatile crops (onion, tomato, potato): MAPE 10–17% with LSTM; 50%+ with ARIMA
- This means: for onion at ₹2,000/quintal, the 7-day forecast error is ±₹200–340

**How to present uncertainty:**
1. Direction only for low-confidence scenarios: "Prices likely rising" / "Prices likely falling" / "Direction unclear"
2. Range band for medium/high confidence: "Expected ₹1,800–₹2,200"
3. Confidence colour: Green (high, CV < 0.2), Yellow (medium, CV 0.2–0.5), Red (low/volatile, CV > 0.5)
4. Never: single point forecast presented as fact

**Platform gap this fills:** No Indian agricultural app currently provides any price forecast. eNAM, agmarknet, Kisan Suvidha, AgriMarket all show only current/historical prices. This is a genuine first-mover opportunity.

**Key constraint:** Data freshness. Price data ends 2025-10-30; all forecasts are conditional on the historical model holding, not live feed. Show data cutoff date prominently.

---

### 2. Seasonal Price Calendar

**What it shows:** Best and worst months to sell a commodity in a state, based on 10 years of aggregated price data.

**Structure that works:**
- 12-bar monthly chart (Jan–Dec) showing median modal price
- Interquartile range bands (25th–75th percentile) to show variability
- "Best 2 months" highlighted with a distinct colour (not just the single best month — monsoon variability can shift the peak by 4–6 weeks)
- "Avoid" months shown in muted colour

**Granularity:** State level is the right default; district level is available but adds noise for seasonal patterns because the same climate zone governs price in a region.

**What Indian platforms do:** agmarknet provides raw monthly data but no aggregation or visual calendar. CEDA Ashoka provides research-grade visualisations but not a farmer-facing calendar. No consumer platform provides this feature. Farmers currently rely on memory, community knowledge, and traders — all of which systematically disadvantage sellers.

**Known seasonal patterns to validate against:**
- Onion: peaks October–November; trough April–May
- Tomato: peaks July (West Bengal), February–March (Karnataka)
- Potato: peaks November; trough March–April
- Wheat: peaks May–June (pre-harvest); troughs October post-Rabi

**Complexity:** Low-Medium. Pure aggregation — no model risk. Highest farmer-value-to-engineering-effort ratio of all four features. Build this first.

---

### 3. Crop Recommendation

**What inputs farmers can realistically provide:**
- District (known), Block (approximately known), Season (Kharif/Rabi/Zaid — known)
- Land size in acres or bighas (known)
- Irrigation availability: Yes/No/Partial (known)
- Last crop grown (usually known; needed for rotation logic)
- What farmers CANNOT reliably provide: field-specific NPK readings, soil pH, precise GPS coordinates

**What the platform provides that farmers can't (the value add):**
- Block-average NPK/pH from Soil Health Card data (84,794 samples across 6,895 blocks)
- Historical rainfall deficit/surplus for the current and recent seasons
- Expected market price for the season based on seasonal calendar

**How to present recommendations:**
- Rank top 3–5 crops for the farmer's block and season
- For each: "Soil suitable? YES/PARTIAL/NO", "Market currently: HIGH/MEDIUM/LOW demand", "Grows well in this season: YES/NO"
- Include fertiliser deficit flag: "Your block is LOW in Nitrogen — this crop needs N; budget for urea"
- Explicit caveat: "Based on [block name] average soil. Your field may differ."

**Granularity verdict:** Block level is correct and sufficient. Village-level would require individual field data not available. District-level would lose the soil variability that makes recommendations actionable. Block is the right granularity given the data asset.

**What Indian platforms do:** Kisan Suvidha shows generic crop advisories from state universities. IFFCO Kisan shows crop-specific cultivation guidance. Neither does soil-deficit-driven ranking. The Soil Health Card scheme provides physical cards but has ~49% follow-through rate and poor farmer comprehension. A digital, simplified version with market signal overlay is a genuine differentiator.

**Nationwide soil deficit context (from data):** 69.7% of blocks are LOW in Nitrogen; 86.9% LOW in pH. This makes the "your block has N deficit, choose a legume to fix it" pattern relevant across most of India, not just edge cases.

---

### 4. Mandi Arbitrage Dashboard

**What thresholds matter:**
- Raw price differential is misleading without transport cost. A ₹200/quintal price difference across 200km may yield negative net profit after diesel, loading/unloading, spoilage, and time.
- The transport logistics engine already computes net profit after freight + spoilage. The arbitrage feature should reuse this: filter to mandis where NET profit (after transport) exceeds a threshold.
- Recommended filter threshold: NET margin > 10% of commodity price after transport. This filters out noise while surfacing genuine opportunities.
- A farmer travelling for ₹50/quintal net gain for a 3-hour journey is not worth it. A ₹400/quintal net gain on a 4-hour journey is.

**How to present price differentials:**
1. Show top 3 mandis ranked by net profit (after transport), not by raw price
2. Show: Distance, Travel time (from routing engine), Net gain per quintal, Verdict badge (WORTH IT / BORDERLINE / NOT WORTH IT)
3. This is what the transport breakdown already does — arbitrage is a logical extension

**What platforms do today:** eNAM and agmarknet show raw prices across mandis. No platform in India currently shows net profit after transport for a given commodity — this is a genuine gap. The AgriMarket app shows "prices within 50km" but with no transport cost calculation.

**What thresholds are real:** Research shows local producers earn 13–73% more selling through mandis vs private traders. The threshold for arbitrage to be meaningful is commodity-dependent: perishables (tomato, leafy greens) have narrow windows due to spoilage, while durables (onion, wheat, potato with storage) can tolerate longer travel times.

---

## Feature Dependencies

```
District Name Harmonisation
    → Seasonal Price Calendar (needs price data + state mapping)
    → Price Forecasting Engine (needs rainfall features from harmonised districts)
    → Crop Recommendation (needs soil data joined to price districts)
    → Mandi Arbitrage (needs routing distances from transport engine)

Seasonal Price Calendar
    → Price Forecasting Engine (calendar provides seasonal baseline, reduces model error)
    → Crop Recommendation (market demand signal comes from seasonal price)

Transport Logistics Engine (already exists)
    → Mandi Arbitrage Dashboard (net-profit calculation reuses existing engine)

Price Forecasting Engine (XGBoost baseline)
    → LSTM Price Forecasting (LSTM improves on XGBoost for volatile crops)
    → "Sell now vs wait" signal (derived from forecast direction)
```

**Critical dependency:** All ML features require district name harmonisation across the four datasets. This is Phase 1 and is not optional. Building anything else before harmonisation produces wrong cross-dataset joins.

---

## MVP Recommendation

Prioritise in this order:

1. **District name harmonisation** — enables everything; pure data engineering; zero UI risk
2. **Seasonal price calendar** — highest farmer value per engineering hour; pure aggregation; no model risk; fills a gap no Indian platform addresses
3. **Price forecasting (XGBoost baseline)** — directional signal for 7 days; frame as "price direction" not "precise prediction"; validate against holdout before release
4. **Mandi arbitrage dashboard** — reuses transport engine; show net-profit-ranked top 3 mandis; filter out sub-threshold differentials
5. **Crop recommendation engine** — highest complexity; needs soil + price + rainfall all harmonised; build last in milestone

Defer:
- **LSTM price forecasting**: Only meaningful improvement over XGBoost for onion/tomato/potato. Build after XGBoost is validated and serving. Do not delay everything else waiting for LSTM.
- **Weather-enhanced model (260 districts)**: Tiered approach — use rainfall for 95% coverage, add weather features for 46%-covered districts as a model improvement, not a blocker.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Price forecasting accuracy benchmarks | MEDIUM | Peer-reviewed 2024 literature on Indian commodities; specific MAPE values validated across multiple papers |
| Seasonal price patterns (TOP crops) | HIGH | Well-documented in both academic literature and government monitoring (MIEWS portal); consistent across sources |
| Competing platform features | HIGH | Directly observed: eNAM, agmarknet, Kisan Suvidha, AgriMarket, IFFCO Kisan all verified; none provide forecasts or net-profit arbitrage |
| UX for low-literacy farmers | MEDIUM | GSMA field research + Ama Krushi study + FarmRise case study; direction is clear (simple, directional, visual) but exact threshold for "too complex" needs user testing |
| Crop recommendation inputs farmers can provide | MEDIUM | Soil Health Card scheme failure modes are well-documented; realistic input set inferred from field research; no direct survey of what AgriProfit's specific farmer segment knows |
| Arbitrage threshold (10% net margin) | LOW | Inferred from transport cost analysis and research on marketing channel price differentials; no primary source gives a specific "minimum viable arbitrage" threshold for Indian farmers |

---

## Sources

- eNAM platform features: https://www.pib.gov.in/FactsheetDetails.aspx?Id=149061 (PIB, 2024)
- Agmarknet platform and CEDA analytics: https://agmarknet.ceda.ashoka.edu.in/ (Ashoka University CEDA)
- Kisan Suvidha features: https://www.gstsuvidhakendra.org/what-is-kisan-suvidha-app/ (MEDIUM confidence)
- Price forecast accuracy benchmarks: https://pmc.ncbi.nlm.nih.gov/articles/PMC12215695/ (PMC, 2025 — 23 Indian commodities, Jan 2010–Jun 2024)
- TOP crop (onion/tomato/potato) price dynamics: https://journalajaees.com/index.php/AJAEES/article/view/2387 (2024)
- Exogenous-variable LSTM for TOP crops: https://www.nature.com/articles/s41598-024-68040-3 (Nature Scientific Reports, 2024)
- Soil Health Card limitations: https://acspublisher.com/journals/index.php/ijee/article/view/10713 (Indian Journal of Extension Education)
- Soil Health Card scheme Wikipedia overview: https://en.wikipedia.org/wiki/Soil_Health_Card_Scheme
- Crop recommendation inputs (ML, NPK, pH): https://www.nature.com/articles/s41598-025-88676-z (Nature Scientific Reports, 2025)
- Marketing channel price differentials (13–73% mandi premium): https://www.sciencedirect.com/science/article/pii/S0313592624000213 (ScienceDirect, 2024)
- Farmer digital literacy and app adoption: https://www.chloropy.com/post/india-s-top-agricultural-apps-leading-the-way-in-2024 (2024)
- Farmer WhatsApp preference vs native apps: https://www.tandfonline.com/doi/full/10.1080/27685241.2024.2420803 (2024 Taylor & Francis)
- Ama Krushi farmer engagement with audio advice: https://precisiondev.org/customized-digital-advice-can-help-farmers-reduce-crop-loss-and-manage-weather-shocks-a-summary-or-as-much-as-we-can-summarize/ (Precision Development)
- AI agri decision support systems survey: https://www.researchgate.net/publication/396527518 (ResearchGate, 2024)
- DeHaat AI advisory: https://thebetterindia.com/farming/dehaat-ai-agritech-platform-indian-farmers-10943764 (The Better India)
- AgriMarket GPS-based features: https://agriinsurance.com/Agri-Insurance-Types/Crop-Insurance-Mobile-App.html
