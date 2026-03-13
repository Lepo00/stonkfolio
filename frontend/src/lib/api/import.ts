import type { ImportPreview, ImportResult } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function uploadCsv(
  portfolioId: number,
  file: File,
  broker: string
): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("broker", broker);

  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/portfolios/${portfolioId}/import/csv/`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function confirmImport(
  portfolioId: number,
  previewId: string
): Promise<ImportResult> {
  const { apiClient } = await import("./client");
  return apiClient<ImportResult>(`/portfolios/${portfolioId}/import/csv/confirm/`, {
    method: "POST",
    body: { preview_id: previewId },
  });
}
