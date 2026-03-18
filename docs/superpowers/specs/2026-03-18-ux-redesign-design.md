# UX Redesign — Premium Fintech Bento Dashboard

**Date**: 2026-03-18
**Status**: Approved

## Summary

Redesign the frontend UX with a premium fintech aesthetic (DM Sans, rounded cards, small caps labels) and an asymmetric bento grid dashboard focused on the 4 most important metrics. Promote AI analysis to hero status on instrument detail. Light refresh on secondary pages.

## 1. Visual System

### Typography

- **Font**: Switch from Inter to **DM Sans** via `next/font/google`
- **Base size**: 18px (set on `html` in globals.css)
- CSS variable: `--font-dm-sans`, mapped to `--font-sans` in Tailwind theme

### Card Style

- Border radius bumped: `--radius: 0.75rem` (from 0.625rem)
- Cards use `rounded-xl shadow-sm`
- Dark mode card bg slightly lighter: `--card: oklch(0.22 0 0)` (from 0.205)

### Labels

- Card labels use small caps style: `text-xs uppercase tracking-wider text-muted-foreground`
- Applied to: "TOTAL VALUE", "TODAY", "OVERALL GAIN/LOSS", "PERFORMANCE", and card headers throughout

### Colors

- Keep existing oklch color system
- Sidebar light bg: `oklch(0.98 0 0)`, dark bg: `oklch(0.16 0 0)`
- Sidebar border softened: `border-r border-border/50`

## 2. Dashboard — Asymmetric Bento Grid

### Layout

CSS Grid: `grid-template-columns: 2fr 1fr`, `gap-4`. Responsive: collapses to single column below `lg` breakpoint.

```
┌─────────────────────────────┬────────────────┐
│  TOTAL VALUE                │  TODAY         │
│  €24,114.16                 │  +€127.50      │
│  ▲ 3.44% all time           │  +0.53%        │
├─────────────────────────────┼────────────────┤
│  PERFORMANCE                │  OVERALL G/L   │
│  [line chart with gradient] │  +€801.98      │
│  [1W][1M][3M][6M][1Y][ALL] │  +3.44%        │
│                             │  Since Jan 2026│
└─────────────────────────────┴────────────────┘
```

### Hero Card (top-left)

- Label: `TOTAL VALUE` in small caps
- Value: `text-4xl font-bold` with `€` prefix
- Below value: overall return as colored text with `TrendingUp`/`TrendingDown` icon inline, e.g. `▲ +3.44% all time` in green
- Card height: auto, roughly ~160px

### Today Card (top-right)

- Label: `TODAY` in small caps
- Value: `text-2xl font-bold`, colored green/red
- Below: percentage change
- `TrendingUp`/`TrendingDown` icon

### Performance Card (bottom-left)

- No title bar — chart speaks for itself
- Recharts `AreaChart` + `Area` with `linearGradient` fill (not `LineChart` — different API)
- Period toggles as small pill buttons at bottom of card: `1W 1M 3M 6M 1Y ALL`
- Chart height: ~280px
- Skeleton loading: `animate-pulse` placeholder matching chart area

### Overall G/L Card (bottom-right)

- Label: `OVERALL GAIN/LOSS` in small caps
- Value: `text-2xl font-bold`, colored green/red
- Percentage below
- Small muted label at bottom: `Since {first_transaction_date}`

### Data Requirements

The current `/api/portfolios/{id}/summary/` returns `total_value`, `total_cost`, `total_gain_loss`, `total_return_pct`. This covers the hero card and overall G/L card.

**Missing**: "today's gain/loss" is not available from any endpoint.

**Solution**: Use the `1W` performance series (already fetched for the chart). Subtract the second-to-last data point from the last data point to get today's change. If only one data point exists or markets are closed (no today data), show `--` as the value instead of `€0.00`.

Note: The backend `PERIOD_MAP` does not support `1D`. The `1W` series provides enough data points to derive today's delta without backend changes.

**Also missing**: `first_transaction_date` for the "Since..." label on the Overall G/L card. **Solution**: Add `first_transaction_date` to the summary endpoint response (minor backend change — one annotation on the queryset, not a new endpoint). Add the field to the `PortfolioSummary` TypeScript type.

### Empty & Loading States

- No portfolio selected: centered empty state with icon + "Create portfolio" CTA (existing pattern)
- Loading: 4 skeleton cards in the same grid layout, `animate-pulse`
- No data: hero card shows `€0.00`, chart shows empty state with chart icon
- Partial failure: if performance API fails but summary succeeds, show the 3 summary cards normally and an error/retry state in the chart card

## 3. Sidebar Refinement

### Expanded State (w-64)

- App name: `text-xl font-bold` in DM Sans
- Background: update `--sidebar` CSS variable to `oklch(0.98 0 0)` light / `oklch(0.16 0 0)` dark. Change sidebar component from `bg-background` to `bg-sidebar`
- Border: `border-r border-border/50`
- Active nav item: **pill-shaped highlight** — `rounded-lg bg-primary/10 text-primary font-semibold` (remove left border indicator)
- Nav icons: bump from `size-4` to `size-5`
- Everything else stays (portfolio selector, theme toggle, user menu, collapse toggle)

### Collapsed State (w-16)

- Active item: filled pill background behind icon
- Same behavior as current

## 4. Instrument Detail — AI Hero Banner

### Current State

AI analysis is a plain card below the chart — easy to miss.

### New Layout (top to bottom)

1. Back button + instrument name/ticker/ISIN (unchanged)
2. **AI Analysis Hero Banner** (new position — promoted from bottom)
3. Details + Price cards (2-column grid, unchanged)
4. Interactive chart (unchanged)
5. News (unchanged)

### AI Hero Banner Design

Full-width card with tinted background based on recommendation:
- BUY: green tint (`bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800`)
- HOLD: amber tint (`bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800`)
- SELL: red tint (`bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800`)

Layout inside the card:
- Top row: Large recommendation badge (BUY/HOLD/SELL) + confidence label on the right
- Middle: Reasoning paragraph (full width)
- Signal badges row: inline bullish/bearish pills
- Bottom: Metrics as a compact grid row (Price, SMA 20, SMA 50, Weekly %, Monthly %)

When analysis is loading: skeleton placeholder with tinted neutral background.
When analysis fails/unavailable: card not shown (don't show empty card).

## 5. Secondary Pages — Light Refresh

No layout changes. They inherit global visual system updates:
- DM Sans font (automatic via CSS variable)
- Rounded corners `rounded-xl` on cards (automatic via `--radius`)
- Card shadows (automatic)
- Small caps labels on card headers where applicable

### Specific Small Changes

- **Performance**: Card header labels in small caps
- **Allocation**: Card header labels in small caps
- **Transactions**: Card header labels in small caps
- **Settings**: No changes needed
- **Import**: No changes needed

## Files Changed

| File | Change |
|------|--------|
| `backend/apps/portfolios/views.py` | Add `first_transaction_date` to summary response |
| `frontend/src/types/api.ts` | Add `first_transaction_date` to `PortfolioSummary` type |
| `app/layout.tsx` | Switch Inter → DM Sans |
| `app/globals.css` | Font variable, base size 18px, radius, dark card bg, sidebar colors |
| `app/(app)/dashboard/page.tsx` | Full rewrite — bento grid layout |
| `app/(app)/instrument/[id]/page.tsx` | Move AI analysis to hero banner position, tinted card |
| `components/layout/sidebar.tsx` | Pill active state, icon size, softer border/bg |
| `app/(app)/performance/page.tsx` | Small caps labels |
| `app/(app)/allocation/page.tsx` | Small caps labels |
| `app/(app)/transactions/page.tsx` | Small caps labels |

## Out of Scope

- Mobile hamburger menu / responsive sidebar collapse
- New backend endpoints (today's G/L computed client-side; `first_transaction_date` is a minor addition to existing endpoint, not a new one)
- Holdings list on dashboard (accessible via Transactions page; holdings view is a future addition)
- Table pagination/sorting on transactions
- Import page redesign
