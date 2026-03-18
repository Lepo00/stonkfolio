"use client";

import { useState } from "react";
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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create portfolio</DialogTitle>
          <DialogDescription>
            Give your portfolio a name to get started.
          </DialogDescription>
        </DialogHeader>
        {open && <CreatePortfolioForm onOpenChange={onOpenChange} />}
      </DialogContent>
    </Dialog>
  );
}

function CreatePortfolioForm({ onOpenChange }: { onOpenChange: (open: boolean) => void }) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { setSelected, refreshPortfolios } = usePortfolio();

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
  );
}
