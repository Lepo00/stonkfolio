import { apiClient } from "./client";
import type { ImportPreview, ImportResult } from "@/types/api";

export async function uploadCsv(
  portfolioId: number,
  file: File,
  broker: string
): Promise<ImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("broker", broker);

  return apiClient<ImportPreview>(`/portfolios/${portfolioId}/import/csv/`, {
    method: "POST",
    body: formData,
  });
}

export async function confirmImport(
  portfolioId: number,
  previewId: string
): Promise<ImportResult> {
  return apiClient<ImportResult>(`/portfolios/${portfolioId}/import/csv/confirm/`, {
    method: "POST",
    body: { preview_id: previewId },
  });
}
