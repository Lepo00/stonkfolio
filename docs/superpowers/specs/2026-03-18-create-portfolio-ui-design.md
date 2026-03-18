# Create Portfolio UI + Visual Polish

**Date**: 2026-03-18
**Status**: Approved

## Summary

Add the ability to create portfolios from the UI via a dialog, and improve overall visual quality by switching to the Inter font with a larger base size.

## Feature: Create Portfolio Dialog

### Components

**`Dialog` UI primitive** — shadcn/ui Dialog (Radix-based). New file at `frontend/src/components/ui/dialog.tsx`.

**`CreatePortfolioDialog`** — New component at `frontend/src/components/portfolios/create-portfolio-dialog.tsx`:
- Controlled dialog via `open` / `onOpenChange` props
- Single-field form: "Portfolio name" text input + "Create" button
- Uses TanStack Query `useMutation` calling existing `createPortfolio()` from `lib/api/portfolios.ts`
- On success: invalidates `["portfolios"]` query, auto-selects the new portfolio, closes dialog
- On error: inline error message below the input. Specifically handle duplicate name (backend has `unique_together = ["user", "name"]`) with "A portfolio with this name already exists."
- Submit disabled while name is empty/whitespace-only or mutation is pending. Trim name before submission.
- Input has `maxLength={100}` to match backend constraint
- Form clears on dialog close. Submit on Enter (standard `<form onSubmit>`)
- Button shows "Creating..." text while mutation is pending

### Trigger Points

1. **Sidebar** — `Plus` icon button next to the "Portfolio" label in the sidebar portfolio selector section
2. **Dashboard empty state** — Replace plain "Create a portfolio to get started" text with a `Button` that opens the dialog

### Data Flow

```
User clicks trigger → Dialog opens → User types name → Submit
  → POST /api/portfolios/ → 201 Created
  → await invalidateQueries(["portfolios"]) → list refreshes
  → setSelected(newPortfolio) after await → sidebar updates
  → Dialog closes
```

## Visual Polish: Font + Sizing

### Font Change

Replace Geist Sans/Mono with **Inter** (Google's product font) as the primary sans-serif font. Keep a monospace fallback for code contexts.

**Changes:**

- `layout.tsx`: Replace `Geist`/`Geist_Mono` imports with `Inter` from `next/font/google`, set `variable: "--font-inter"`
- `globals.css`: Update `--font-sans` in `@theme inline` to `var(--font-inter)`

### Base Font Size

Bump the default `html` font size from browser default 16px to **17px** via `globals.css`. This makes all `rem`-based sizing slightly larger throughout the app without touching individual components.

## Files Changed

| File | Change |
|------|--------|
| `components/ui/dialog.tsx` | New — shadcn/ui Dialog primitive |
| `components/portfolios/create-portfolio-dialog.tsx` | New — dialog with form + mutation logic |
| `components/layout/sidebar.tsx` | Add "+" button, render CreatePortfolioDialog |
| `app/(app)/dashboard/page.tsx` | Add CTA button in empty state, render CreatePortfolioDialog |
| `app/layout.tsx` | Switch from Geist to Inter font |
| `app/globals.css` | Update font variable, add `font-size: 17px` to html |

## Out of Scope

- Portfolio rename/delete (future work)
- Additional form fields (description, currency)
- Backend changes (API already supports POST /api/portfolios/)