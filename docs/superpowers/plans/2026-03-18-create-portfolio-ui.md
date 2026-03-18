# Create Portfolio UI + Visual Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to create portfolios from the UI via a dialog, and improve visual quality with Inter font + larger base size.

**Architecture:** A `CreatePortfolioDialog` component uses TanStack Query `useMutation` to call the existing `createPortfolio` API. The dialog is triggered from a "+" button in the sidebar and a CTA on the dashboard empty state. Font/sizing changes are global CSS updates.

**Tech Stack:** Next.js 16, React 19, shadcn/ui v4 (base-nova style, @base-ui/react), TanStack Query v5, Tailwind v4

**Spec:** `docs/superpowers/specs/2026-03-18-create-portfolio-ui-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/components/ui/dialog.tsx` | Create | shadcn/ui Dialog primitive (via CLI) |
| `frontend/src/components/portfolios/create-portfolio-dialog.tsx` | Create | Dialog with name form, mutation, error handling |
| `frontend/src/lib/portfolio-context.tsx` | Modify | Expose `refreshPortfolios` for post-create invalidation |
| `frontend/src/components/layout/sidebar.tsx` | Modify | Add "+" trigger button |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modify | Add CTA button in empty state |
| `frontend/src/app/layout.tsx` | Modify | Switch Geist → Inter font |
| `frontend/src/app/globals.css` | Modify | Update font variable, add 17px base size |
| `frontend/src/__tests__/create-portfolio-dialog.test.tsx` | Create | Tests for dialog component |

---

### Task 1: Add shadcn/ui Dialog primitive

**Files:**
- Create: `frontend/src/components/ui/dialog.tsx`

- [ ] **Step 1: Install Dialog via shadcn CLI**

```bash
cd frontend && npx shadcn@latest add dialog
```

This creates `src/components/ui/dialog.tsx` using `@base-ui/react/dialog` (matching the project's base-nova style).

- [ ] **Step 2: Verify the component was created**

```bash
ls -la frontend/src/components/ui/dialog.tsx
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/dialog.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: add shadcn/ui dialog primitive"
```

---

### Task 2: Switch font from Geist to Inter

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Update layout.tsx to use Inter**

Replace the font imports and configuration in `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Stonkfolio",
  description: "Portfolio tracker for your investments",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Update globals.css font variable and base size**

In `frontend/src/app/globals.css`, change `--font-sans` in the `@theme inline` block:

```css
--font-sans: var(--font-inter);
```

(Was: `--font-sans: var(--font-sans);`)

Also remove the `--font-mono: var(--font-geist-mono);` line (no longer used).

In the `@layer base` block, update the `html` rule to add the font size:

```css
html {
  @apply font-sans;
  font-size: 17px;
}
```

- [ ] **Step 3: Verify dev server renders with new font**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "style: switch to Inter font and bump base size to 17px"
```

---

### Task 3: Expose query invalidation from portfolio context

**Files:**
- Modify: `frontend/src/lib/portfolio-context.tsx`

- [ ] **Step 1: Add `refreshPortfolios` to the context**

The `CreatePortfolioDialog` needs to invalidate the portfolios query and auto-select the new portfolio after creation. Add `useQueryClient` and expose a refresh function.

Update `frontend/src/lib/portfolio-context.tsx`:

Add to imports:
```tsx
import { useQuery, useQueryClient } from "@tanstack/react-query";
```

Add to `PortfolioContextType`:
```tsx
interface PortfolioContextType {
  portfolios: Portfolio[];
  selected: Portfolio | null;
  setSelected: (p: Portfolio) => void;
  refreshPortfolios: () => Promise<void>;
}
```

Inside `PortfolioProvider`, add:
```tsx
const queryClient = useQueryClient();

const refreshPortfolios = useCallback(async () => {
  await queryClient.invalidateQueries({ queryKey: ["portfolios"] });
}, [queryClient]);
```

Update the Provider value:
```tsx
<PortfolioContext.Provider value={{ portfolios, selected, setSelected, refreshPortfolios }}>
```

- [ ] **Step 2: Verify build passes**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/portfolio-context.tsx
git commit -m "feat: expose refreshPortfolios from portfolio context"
```

---

### Task 4: Create the CreatePortfolioDialog component

**Files:**
- Create: `frontend/src/components/portfolios/create-portfolio-dialog.tsx`

- [ ] **Step 1: Write the component**

Create `frontend/src/components/portfolios/create-portfolio-dialog.tsx`:

```tsx
"use client";

import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { createPortfolio } from "@/lib/api/portfolios";
import { usePortfolio } from "@/lib/portfolio-context";
import { ApiError } from "@/lib/api/client";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CreatePortfolioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreatePortfolioDialog({ open, onOpenChange }: CreatePortfolioDialogProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { setSelected, refreshPortfolios } = usePortfolio();

  // Clear form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setName("");
      setError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: (portfolioName: string) => createPortfolio(portfolioName.trim()),
    onSuccess: async (newPortfolio) => {
      await refreshPortfolios();
      setSelected(newPortfolio);
      onOpenChange(false);
    },
    onError: (err: Error) => {
      if (err instanceof ApiError && err.data) {
        const data = err.data as Record<string, string[]>;
        if (data.name) {
          setError("A portfolio with this name already exists.");
          return;
        }
        if (data.non_field_errors) {
          setError(data.non_field_errors[0]);
          return;
        }
      }
      setError("Failed to create portfolio. Please try again.");
    },
  });

  const trimmedName = name.trim();
  const canSubmit = trimmedName.length > 0 && !mutation.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSubmit) {
      setError(null);
      mutation.mutate(name);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create portfolio</DialogTitle>
          <DialogDescription>
            Give your portfolio a name to get started.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="space-y-2 py-4">
            <Label htmlFor="portfolio-name">Name</Label>
            <Input
              id="portfolio-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Long-term investments"
              maxLength={100}
              autoFocus
            />
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {mutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 2: Verify build passes**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/portfolios/create-portfolio-dialog.tsx
git commit -m "feat: add CreatePortfolioDialog component"
```

---

### Task 5: Add "+" trigger button to sidebar

**Files:**
- Modify: `frontend/src/components/layout/sidebar.tsx`

- [ ] **Step 1: Update sidebar imports**

Add to the lucide-react import in `frontend/src/components/layout/sidebar.tsx`:

```tsx
import { Plus } from "lucide-react";
```

(Add `Plus` to the existing destructured import.)

Add the dialog import:

```tsx
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";
```

- [ ] **Step 2: Add state and render dialog**

Inside the `Sidebar` component function, add state:

```tsx
const [createOpen, setCreateOpen] = useState(false);
```

Add `useState` import at the top of the file (sidebar.tsx does not currently import from `"react"`):

```tsx
import { useState } from "react";
```

At the end of the component, just before the closing `</aside>`, add:

```tsx
<CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
```

- [ ] **Step 3: Add "+" button next to the Portfolio label**

Replace the portfolio selector section (lines 74-96) — specifically the label line — to include a "+" button:

Change:
```tsx
<label className="mb-1.5 block text-xs font-medium text-muted-foreground">
  Portfolio
</label>
```

To:
```tsx
<div className="mb-1.5 flex items-center justify-between">
  <label className="text-xs font-medium text-muted-foreground">
    Portfolio
  </label>
  <Button
    variant="ghost"
    size="icon-xs"
    onClick={() => setCreateOpen(true)}
    className="text-muted-foreground hover:text-foreground"
    aria-label="Create portfolio"
  >
    <Plus className="size-3.5" />
  </Button>
</div>
```

- [ ] **Step 4: Verify build passes**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/sidebar.tsx
git commit -m "feat: add create portfolio button to sidebar"
```

---

### Task 6: Add CTA button to dashboard empty state

**Files:**
- Modify: `frontend/src/app/(app)/dashboard/page.tsx`

- [ ] **Step 1: Add imports**

Add to `frontend/src/app/(app)/dashboard/page.tsx`:

```tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";
```

- [ ] **Step 2: Add state**

Inside `DashboardPage`, add at the top of the function:

```tsx
const [createOpen, setCreateOpen] = useState(false);
```

- [ ] **Step 3: Update the empty state block**

Replace the current empty state (lines 33-42):

```tsx
if (!selected) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-muted-foreground mt-4">
        Create a portfolio to get started
      </p>
    </div>
  );
}
```

With:

```tsx
if (!selected) {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-muted-foreground mt-4">
        Create a portfolio to get started.
      </p>
      <Button className="mt-4" onClick={() => setCreateOpen(true)}>
        <Plus className="size-4" data-icon="inline-start" />
        Create portfolio
      </Button>
      <CreatePortfolioDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
```

- [ ] **Step 4: Verify build passes**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/(app)/dashboard/page.tsx
git commit -m "feat: add create portfolio CTA to dashboard empty state"
```

---

### Task 7: Write tests for CreatePortfolioDialog

**Files:**
- Create: `frontend/src/__tests__/create-portfolio-dialog.test.tsx`

- [ ] **Step 1: Write tests**

Create `frontend/src/__tests__/create-portfolio-dialog.test.tsx`:

```tsx
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";

// Mock dependencies
const mockSetSelected = jest.fn();
const mockRefreshPortfolios = jest.fn().mockResolvedValue(undefined);

jest.mock("@/lib/portfolio-context", () => ({
  usePortfolio: () => ({
    portfolios: [],
    selected: null,
    setSelected: mockSetSelected,
    refreshPortfolios: mockRefreshPortfolios,
  }),
}));

const mockMutate = jest.fn();
let mockMutationState = { isPending: false };

jest.mock("@tanstack/react-query", () => ({
  useMutation: ({ mutationFn, onSuccess, onError }: {
    mutationFn: (name: string) => Promise<unknown>;
    onSuccess: (data: unknown) => void;
    onError: (err: Error) => void;
  }) => ({
    mutate: (name: string) => {
      mockMutate(name);
      mutationFn(name).then(onSuccess).catch(onError);
    },
    ...mockMutationState,
  }),
}));

jest.mock("@/lib/api/portfolios", () => ({
  createPortfolio: jest.fn().mockResolvedValue({ id: 1, name: "Test", created_at: "2026-01-01" }),
}));

// Mock UI components for testing
jest.mock("@/components/ui/input", () => ({
  Input: (props: React.ComponentProps<"input">) =>
    React.createElement("input", props),
}));

jest.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("CreatePortfolioDialog", () => {
  const onOpenChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockMutationState = { isPending: false };
  });

  it("renders dialog content when open", () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    expect(screen.getByText("Create portfolio")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<CreatePortfolioDialog open={false} onOpenChange={onOpenChange} />);
    expect(screen.queryByText("Create portfolio")).not.toBeInTheDocument();
  });

  it("disables submit when name is empty", () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).toBeDisabled();
  });

  it("disables submit when name is whitespace only", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "   ");
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).toBeDisabled();
  });

  it("enables submit when name has content", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "My Portfolio");
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).not.toBeDisabled();
  });

  it("calls mutate on form submit", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "My Portfolio");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(mockMutate).toHaveBeenCalledWith("My Portfolio");
  });

  it("calls cancel to close dialog", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("clears input when dialog reopens", () => {
    const { rerender } = render(
      <CreatePortfolioDialog open={false} onOpenChange={onOpenChange} />
    );
    rerender(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    expect(screen.getByLabelText("Name")).toHaveValue("");
  });

  it("on success: refreshes, selects, and closes", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "Test");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => {
      expect(mockRefreshPortfolios).toHaveBeenCalled();
      expect(mockSetSelected).toHaveBeenCalledWith({ id: 1, name: "Test", created_at: "2026-01-01" });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npm test -- --testPathPattern=create-portfolio-dialog
```

Expected: All tests pass.

- [ ] **Step 3: Run full test suite to check for regressions**

```bash
cd frontend && npm test
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/__tests__/create-portfolio-dialog.test.tsx
git commit -m "test: add CreatePortfolioDialog tests"
```

---

### Task 8: Final lint and build verification

- [ ] **Step 1: Run linter**

```bash
cd frontend && npx eslint src/
```

Expected: No errors.

- [ ] **Step 2: Run production build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Run all tests**

```bash
cd frontend && npm test
```

Expected: All tests pass.