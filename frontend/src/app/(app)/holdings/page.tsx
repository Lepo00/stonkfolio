"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Briefcase } from "lucide-react";
import { usePortfolio } from "@/lib/portfolio-context";
import { getHoldings } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function HoldingsPage() {
  const router = useRouter();
  const { selected } = usePortfolio();

  const { data, isLoading, error } = useQuery({
    queryKey: ["holdings", selected?.id],
    queryFn: () => getHoldings(selected!.id),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Holdings</h1>
        <p className="text-muted-foreground mt-1">Your current positions.</p>
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Briefcase className="size-12 mb-3 opacity-30" />
          <p>Select a portfolio to view holdings.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load holdings. Please try again.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Holdings</h1>
          <p className="text-muted-foreground mt-1">Your current positions.</p>
        </div>
        <Card className="shadow-sm rounded-xl">
          <CardContent className="space-y-3 pt-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="animate-pulse bg-muted rounded h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    );
  }

  const holdings = data?.results ?? [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Holdings</h1>
        <p className="text-muted-foreground mt-1">Your current positions.</p>
      </div>

      <Card className="shadow-sm rounded-xl">
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Positions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {holdings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <Briefcase className="size-10 opacity-40" />
              <p className="text-sm">No holdings yet</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Avg Buy Price</TableHead>
                  <TableHead className="text-right">Cost Basis</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holdings.map((h) => {
                  const qty = parseFloat(h.quantity);
                  const avgPrice = parseFloat(h.avg_buy_price);
                  const costBasis = qty * avgPrice;
                  return (
                    <TableRow
                      key={h.id}
                      className="cursor-pointer hover:bg-muted/50"
                      role="link"
                      tabIndex={0}
                      onClick={() => router.push(`/instrument/${h.instrument.id}`)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          router.push(`/instrument/${h.instrument.id}`);
                        }
                      }}
                    >
                      <TableCell className="font-medium">
                        {h.instrument.name}
                      </TableCell>
                      <TableCell>{h.instrument.ticker ?? "-"}</TableCell>
                      <TableCell className="text-right">
                        {qty.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 4,
                        })}
                      </TableCell>
                      <TableCell className="text-right">
                        €{avgPrice.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </TableCell>
                      <TableCell className="text-right">
                        €{costBasis.toLocaleString(undefined, {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
