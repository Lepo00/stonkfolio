import { apiClient } from "./client";
import type {
  Portfolio, Holding, Transaction, PortfolioSummary,
  PerformanceSeries, AllocationItem, PaginatedResponse,
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

export async function getSummary(portfolioId: number) {
  return apiClient<PortfolioSummary>(`/portfolios/${portfolioId}/summary/`);
}

export async function getPerformance(portfolioId: number, period: string) {
  return apiClient<PerformanceSeries>(`/portfolios/${portfolioId}/performance/?period=${period}`);
}

export async function getAllocation(portfolioId: number, groupBy: string) {
  return apiClient<AllocationItem[]>(`/portfolios/${portfolioId}/allocation/?group_by=${groupBy}`);
}

export async function getTransactions(portfolioId: number) {
  return apiClient<PaginatedResponse<Transaction>>(`/portfolios/${portfolioId}/transactions/`);
}
