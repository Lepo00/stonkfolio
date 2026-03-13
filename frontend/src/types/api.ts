export interface User {
  id: number;
  username: string;
  email: string;
  base_currency: string;
}

export interface Instrument {
  id: number;
  isin: string;
  ticker: string | null;
  name: string;
  currency: string;
  sector: string | null;
  country: string | null;
  asset_type: string;
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string;
}

export interface Holding {
  id: number;
  instrument: Instrument;
  quantity: string;
  avg_buy_price: string;
}

export interface Transaction {
  id: number;
  instrument: Instrument;
  type: "BUY" | "SELL" | "DIVIDEND" | "FEE" | "FX";
  quantity: string;
  price: string;
  fee: string;
  date: string;
  broker_source: string;
  broker_reference: string;
}

export interface PortfolioSummary {
  total_value: string;
  total_cost: string;
  total_gain_loss: string;
  total_return_pct: string;
}

export interface PerformanceSeries {
  series: { date: string; value: string }[];
}

export interface AllocationItem {
  group: string;
  value: string;
  percentage: string;
}

export interface PaginatedResponse<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ImportPreview {
  preview_id: string;
  transactions: {
    isin: string;
    product_name: string;
    type: string;
    quantity: string;
    price: string;
    date: string;
    currency: string;
  }[];
}

export interface ImportResult {
  imported: number;
  skipped: number;
  warnings: string[];
}
