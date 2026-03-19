import { apiClient } from "./client";
import type {
  Portfolio, Holding, Transaction, PortfolioSummary,
  PerformanceSeries, AllocationItem, PaginatedResponse,
  AdviceResponse, FullAdviceResponse, DividendResponse,
} from "@/types/api";

export async function listPortfolios() {
  return apiClient<PaginatedResponse<Portfolio>>("/portfolios/");
}

export async function createPortfolio(name: string) {
  return apiClient<Portfolio>("/portfolios/", { method: "POST", body: { name } });
}

export async function deletePortfolio(id: number) {
  return apiClient<void>(`/portfolios/${id}/`, { method: "DELETE" });
}

export async function getHoldings(portfolioId: number) {
  return apiClient<PaginatedResponse<Holding>>(`/portfolios/${portfolioId}/holdings/`);
}

export async function getSummary(portfolioId: number, benchmark?: string) {
  const params = benchmark ? `?benchmark=${benchmark}` : "";
  return apiClient<PortfolioSummary>(`/portfolios/${portfolioId}/summary/${params}`);
}

export async function getPerformance(portfolioId: number, period: string, benchmark?: string) {
  const params = new URLSearchParams({ period });
  if (benchmark) params.set("benchmark", benchmark);
  return apiClient<PerformanceSeries>(`/portfolios/${portfolioId}/performance/?${params.toString()}`);
}

export async function getAllocation(portfolioId: number, groupBy: string) {
  return apiClient<AllocationItem[]>(`/portfolios/${portfolioId}/allocation/?group_by=${groupBy}`);
}

export async function getTransactions(portfolioId: number) {
  return apiClient<PaginatedResponse<Transaction>>(`/portfolios/${portfolioId}/transactions/`);
}

export async function getPortfolioAdvice(portfolioId: number) {
  return apiClient<AdviceResponse>(`/portfolios/${portfolioId}/advice/`);
}

export async function getFullAdvice(portfolioId: number) {
  return apiClient<FullAdviceResponse>(`/portfolios/${portfolioId}/advice/full/`);
}

export async function sendAdviceChat(portfolioId: number, message: string) {
  return apiClient<{ reply: string }>(`/portfolios/${portfolioId}/advice/chat/`, {
    method: "POST",
    body: { message },
  });
}

export async function getDividends(portfolioId: number) {
  return apiClient<DividendResponse>(`/portfolios/${portfolioId}/dividends/`);
}
