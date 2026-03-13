"use client";

import { useState, useRef } from "react";
import { usePortfolio } from "@/lib/portfolio-context";
import { uploadCsv, confirmImport } from "@/lib/api/import";
import type { ImportPreview, ImportResult } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

type FlowState = "upload" | "preview" | "confirming" | "done";

export default function ImportPage() {
  const { selected } = usePortfolio();
  const fileRef = useRef<HTMLInputElement>(null);
  const [broker, setBroker] = useState("degiro");
  const [flowState, setFlowState] = useState<FlowState>("upload");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  if (!selected) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold">Import</h1>
        <p className="text-muted-foreground mt-4">
          Create a portfolio to get started
        </p>
      </div>
    );
  }

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);
    try {
      const data = await uploadCsv(selected.id, file, broker);
      setPreview(data);
      setFlowState("preview");
    } catch {
      setError("Failed to upload file. Please check the format and try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;

    setError(null);
    setFlowState("confirming");
    try {
      const data = await confirmImport(selected.id, preview.preview_id);
      setResult(data);
      setFlowState("done");
    } catch {
      setError("Failed to confirm import.");
      setFlowState("preview");
    }
  };

  const handleReset = () => {
    setFlowState("upload");
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Import</h1>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-red-800 text-sm">
          {error}
        </div>
      )}

      {flowState === "upload" && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Transactions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="broker">Broker</Label>
              <Select value={broker} onValueChange={(v) => v && setBroker(v)}>
                <SelectTrigger id="broker" className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="degiro">DeGiro</SelectItem>
                  <SelectItem value="trade_republic">Trade Republic</SelectItem>
                  <SelectItem value="interactive_brokers">Interactive Brokers</SelectItem>
                  <SelectItem value="bitpanda">Bitpanda</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="csv-file">CSV File</Label>
              <Input
                id="csv-file"
                type="file"
                accept=".csv"
                ref={fileRef}
              />
            </div>

            <Button onClick={handleUpload} disabled={uploading}>
              {uploading ? "Uploading..." : "Upload"}
            </Button>
          </CardContent>
        </Card>
      )}

      {flowState === "preview" && preview && (
        <Card>
          <CardHeader>
            <CardTitle>Preview Transactions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              {preview.transactions.length} transaction(s) found. Review and
              confirm to import.
            </p>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Product</TableHead>
                  <TableHead>ISIN</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead>Currency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {preview.transactions.map((t, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      {new Date(t.date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="font-medium">
                      {t.product_name}
                    </TableCell>
                    <TableCell>{t.isin}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{t.type}</Badge>
                    </TableCell>
                    <TableCell className="text-right">{t.quantity}</TableCell>
                    <TableCell className="text-right">{t.price}</TableCell>
                    <TableCell>{t.currency}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <div className="flex gap-2">
              <Button onClick={handleConfirm}>Confirm Import</Button>
              <Button variant="outline" onClick={handleReset}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {flowState === "confirming" && (
        <Card>
          <CardContent className="py-8">
            <p className="text-muted-foreground">Importing transactions...</p>
          </CardContent>
        </Card>
      )}

      {flowState === "done" && result && (
        <Card>
          <CardHeader>
            <CardTitle>Import Complete</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  {result.imported}
                </p>
                <p className="text-sm text-muted-foreground">Imported</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600">
                  {result.skipped}
                </p>
                <p className="text-sm text-muted-foreground">Skipped</p>
              </div>
            </div>

            {result.warnings.length > 0 && (
              <div className="space-y-1">
                <p className="text-sm font-medium">Warnings:</p>
                <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                  {result.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <Button onClick={handleReset}>Import More</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
