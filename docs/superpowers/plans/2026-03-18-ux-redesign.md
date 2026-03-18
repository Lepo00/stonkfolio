# UX Redesign — Premium Fintech Bento Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the dashboard as an asymmetric bento grid, switch to DM Sans, apply premium fintech styling, and promote AI analysis to hero banner on instrument detail.

**Architecture:** Global visual system changes (font, radius, colors) applied via CSS/layout. Dashboard fully rewritten with bento grid. Sidebar refined. Instrument detail reordered with new AI hero banner. Secondary pages get light label refresh. One minor backend change to add `first_transaction_date` to summary.

**Tech Stack:** Next.js 16, React 19, shadcn/ui v4, TanStack Query v5, Tailwind v4, Recharts (AreaChart), DM Sans (Google Fonts)

**Spec:** `docs/superpowers/specs/2026-03-18-ux-redesign-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/app/layout.tsx` | Modify | Switch Inter → DM Sans |
| `frontend/src/app/globals.css` | Modify | Font var, base size 18px, radius 0.75rem, card/sidebar colors |
| `backend/apps/portfolios/views.py` | Modify | Add `first_transaction_date` to summary response |
| `frontend/src/types/api.ts` | Modify | Add `first_transaction_date` to PortfolioSummary |
| `frontend/src/app/(app)/dashboard/page.tsx` | Rewrite | Bento grid with 4 cards + performance chart |
| `frontend/src/components/layout/sidebar.tsx` | Modify | Pill active state, icon size, bg-sidebar, softer border |
| `frontend/src/app/(app)/instrument/[id]/page.tsx` | Modify | AI hero banner at top, tinted card |
| `frontend/src/app/(app)/performance/page.tsx` | Modify | Small caps labels |
| `frontend/src/app/(app)/allocation/page.tsx` | Modify | Small caps labels |
| `frontend/src/app/(app)/transactions/page.tsx` | Modify | Small caps labels |

---

### Task 1: Switch to DM Sans + global visual system

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Update layout.tsx**

Replace the font import and config:

```tsx
import { DM_Sans } from "next/font/google";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
});
```

Update the body className to use `dmSans.variable` instead of `inter.variable`.

- [ ] **Step 2: Update globals.css**

In `@theme inline` block, change:
```css
--font-sans: var(--font-dm-sans);
```

In `:root`, change:
```css
--radius: 0.75rem;
--sidebar: oklch(0.98 0 0);
```

In `.dark`, change:
```css
--card: oklch(0.22 0 0);
--sidebar: oklch(0.16 0 0);
```

In `@layer base`, change html font size:
```css
html {
  @apply font-sans;
  font-size: 18px;
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "style: switch to DM Sans, bump radius/size, refine colors"
```

---

### Task 2: Add first_transaction_date to backend summary

**Files:**
- Modify: `backend/apps/portfolios/views.py`
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Update PortfolioSummaryView**

In `backend/apps/portfolios/views.py`, inside `PortfolioSummaryView.get()`, after computing totals, add:

```python
first_tx = portfolio.transactions.order_by("date").values_list("date", flat=True).first()
```

Add to the response dict:
```python
"first_transaction_date": str(first_tx) if first_tx else None,
```

- [ ] **Step 2: Update TypeScript type**

In `frontend/src/types/api.ts`, add to `PortfolioSummary`:
```typescript
first_transaction_date: string | null;
```

- [ ] **Step 3: Run backend tests**

```bash
docker compose exec backend python -m pytest apps/portfolios/tests/ -v --tb=short
```

- [ ] **Step 4: Commit**

```bash
git add backend/apps/portfolios/views.py frontend/src/types/api.ts
git commit -m "feat: add first_transaction_date to portfolio summary"
```

---

### Task 3: Rewrite dashboard as bento grid

**Files:**
- Rewrite: `frontend/src/app/(app)/dashboard/page.tsx`

This is the largest task. The dashboard becomes an asymmetric 2fr/1fr bento grid with 4 cards: Hero (total value), Today's G/L, Performance chart, Overall G/L.

- [ ] **Step 1: Write the new dashboard**

Full rewrite of `frontend/src/app/(app)/dashboard/page.tsx`. Key elements:

**Imports needed:**
```tsx
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { usePortfolio } from "@/lib/portfolio-context";
import { getSummary, getPerformance } from "@/lib/api/portfolios";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";
```

**Data hooks:**
- `getSummary(selected.id)` for total value, cost, gain/loss, return %, first_transaction_date
- `getPerformance(selected.id, period)` for the chart + today's G/L derivation

**Today's G/L computation:**
```tsx
const series = perfData?.series ?? [];
const todayGL = series.length >= 2
  ? parseFloat(series[series.length - 1].value) - parseFloat(series[series.length - 2].value)
  : null;
const todayPct = todayGL !== null && series.length >= 2
  ? (todayGL / parseFloat(series[series.length - 2].value)) * 100
  : null;
```

**Grid layout:**
```tsx
<div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-4">
  {/* Hero: Total Value */}
  <Card className="rounded-xl shadow-sm">...</Card>
  {/* Today's G/L */}
  <Card className="rounded-xl shadow-sm">...</Card>
  {/* Performance Chart */}
  <Card className="rounded-xl shadow-sm">...</Card>
  {/* Overall G/L */}
  <Card className="rounded-xl shadow-sm">...</Card>
</div>
```

**Card labels** use small caps: `<p className="text-xs uppercase tracking-wider text-muted-foreground">TOTAL VALUE</p>`

**Hero card**: `text-4xl font-bold` for value. Below: colored return line with TrendingUp/Down icon.

**Performance card**: Recharts `AreaChart` with gradient:
```tsx
<defs>
  <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stopColor="#2563eb" stopOpacity={0.3} />
    <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
  </linearGradient>
</defs>
<Area type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} fill="url(#valueGradient)" dot={false} />
```

Period toggles at bottom of card as small pill buttons.

**Today card**: Shows `todayGL` formatted with €, or `--` if null. TrendingUp/Down icon.

**Overall G/L card**: Shows gain_loss and return_pct. At bottom: `Since {first_transaction_date}` formatted as month/year.

**Skeleton loading**: 4 skeleton cards in the same grid.

**Empty state**: Same "Create portfolio" CTA pattern.

**Partial error**: If summary fails, show error. If only performance fails, show 3 summary cards + error state in chart card.

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Run tests**

```bash
cd frontend && npm test
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/dashboard/page.tsx
git commit -m "feat: rewrite dashboard as asymmetric bento grid"
```

---

### Task 4: Refine sidebar styling

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1: Apply sidebar changes**

1. Change `bg-background` to `bg-sidebar` on the `<aside>` element (line 69)
2. Change `border-r` to `border-r border-border/50` on the `<aside>` element
3. Change app name from `text-lg` to `text-xl font-bold` (line 76)
4. Remove `border-l-2 border-primary` from active nav item (line 164), keep `rounded-lg bg-primary/10 text-primary font-semibold`
5. Change nav icon size from `size-4` to `size-5` (line 168)

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/sidebar.tsx
git commit -m "style: refine sidebar with pill active state and softer styling"
```

---

### Task 5: AI hero banner on instrument detail

**Files:**
- Modify: `frontend/src/app/(app)/instrument/[id]/page.tsx`

- [ ] **Step 1: Reorder and restyle AI analysis**

Move the AI analysis section from below the chart to directly after the instrument name/header (position 2 in the page).

Create a tinted card based on recommendation:

```tsx
const tintClasses: Record<string, string> = {
  BUY: "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800",
  HOLD: "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800",
  SELL: "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800",
};
```

Layout inside the card:
- Top row: Large badge (BUY/HOLD/SELL) + confidence label right-aligned
- Middle: Reasoning paragraph
- Signal badges inline
- Bottom: Metrics grid row (5 columns)

When loading: skeleton with `bg-muted` neutral tint.
When error/unavailable: don't render the card.

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(app\)/instrument/\[id\]/page.tsx
git commit -m "feat: promote AI analysis to tinted hero banner on instrument detail"
```

---

### Task 6: Small caps labels on secondary pages

**Files:**
- Modify: `frontend/src/app/(app)/performance/page.tsx`
- Modify: `frontend/src/app/(app)/allocation/page.tsx`
- Modify: `frontend/src/app/(app)/transactions/page.tsx`

- [ ] **Step 1: Update CardTitle classes**

On each page, find `<CardTitle>` elements and add small caps styling. Change from:
```tsx
<CardTitle>Portfolio Value Over Time</CardTitle>
```
To:
```tsx
<CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Portfolio Value Over Time</CardTitle>
```

Apply to:
- Performance: "Portfolio Value Over Time"
- Allocation: "Portfolio Allocation"
- Transactions: "Transaction History"

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Run all tests**

```bash
cd frontend && npm test
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(app\)/performance/page.tsx frontend/src/app/\(app\)/allocation/page.tsx frontend/src/app/\(app\)/transactions/page.tsx
git commit -m "style: apply small caps labels to secondary page card headers"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run frontend lint**

```bash
cd frontend && npx eslint src/
```

- [ ] **Step 2: Run frontend build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Run all frontend tests**

```bash
cd frontend && npm test
```

- [ ] **Step 4: Run backend tests**

```bash
docker compose exec backend python -m pytest -v --tb=short
```

- [ ] **Step 5: Run backend lint**

```bash
docker compose exec backend ruff check . && docker compose exec backend ruff format --check .
```
