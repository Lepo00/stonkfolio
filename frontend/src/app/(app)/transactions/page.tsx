"use client";

import { useQuery } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getTransactions } from "@/lib/api/portfolios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

const typeBadgeClass: Record<string, string> = {
  BUY: "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900 dark:text-green-400 dark:hover:bg-green-900",
  SELL: "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-900 dark:text-red-400 dark:hover:bg-red-900",
  DIVIDEND: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  FEE: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  FX: "bg-gray-100 text-gray-800 hover:bg-gray-100",
};

export default function TransactionsPage() {
  const { selected } = usePortfolio();

  const { data, isLoading, error } = useQuery({
    queryKey: ["transactions", selected?.id],
    queryFn: () => getTransactions(selected!.id),
    enabled: !!selected,
  });

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <p className="text-muted-foreground mt-4">
          Create a portfolio to get started
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-destructive">Failed to load portfolio data. Please try again.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Transactions</h1>
        <p className="text-muted-foreground mt-4">Loading...</p>
      </div>
    );
  }

  const transactions = data?.results ?? [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Transactions</h1>

      <Card>
        <CardHeader>
          <CardTitle>Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <p className="text-muted-foreground">No transactions yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell>
                      {new Date(t.date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="font-medium">
                      {t.instrument.ticker ?? t.instrument.name}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className={typeBadgeClass[t.type] ?? ""}
                      >
                        {t.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {parseFloat(t.quantity).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 4,
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      {parseFloat(t.price).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      {parseFloat(t.fee).toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
