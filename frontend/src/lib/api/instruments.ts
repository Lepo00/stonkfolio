import { apiClient } from "./client";
import type { InstrumentDetail, StockAnalysis } from "@/types/api";

export async function getInstrumentDetail(id: number) {
  return apiClient<InstrumentDetail>(`/instruments/${id}/`);
}

export async function getInstrumentAnalysis(id: number) {
  return apiClient<StockAnalysis>(`/instruments/${id}/analysis/`);
}
