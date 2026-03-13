import { apiClient } from "./client";
import type { InstrumentDetail, StockAnalysis, ChartData } from "@/types/api";

export async function getInstrumentDetail(id: number) {
  return apiClient<InstrumentDetail>(`/instruments/${id}/`);
}

export async function getInstrumentAnalysis(id: number) {
  return apiClient<StockAnalysis>(`/instruments/${id}/analysis/`);
}

export async function getInstrumentChart(id: number, period: string = "6M") {
  return apiClient<ChartData>(`/instruments/${id}/chart/?period=${period}`);
}
