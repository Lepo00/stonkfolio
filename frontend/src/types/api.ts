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
  first_transaction_date: string | null;
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

export interface InstrumentDetail extends Instrument {
  current_price: string | null;
  price_currency: string | null;
  news: NewsItem[];
}

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published: string;
  thumbnail: string;
}

export interface StockAnalysis {
  recommendation: "BUY" | "HOLD" | "SELL";
  confidence: "low" | "medium" | "high";
  reasoning: string;
  signals: { signal: string; sentiment: "bullish" | "bearish" }[];
  metrics: {
    current_price: string;
    sma_20: string;
    sma_50: string;
    weekly_change_pct: string;
    monthly_change_pct: string;
  };
}

export interface OHLCPoint {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time: string | number;
  value: number;
}

export interface ChartData {
  ticker: string;
  currency: string;
  ohlc: OHLCPoint[];
  indicators: {
    sma_20: IndicatorPoint[];
    sma_50: IndicatorPoint[];
    rsi_14: IndicatorPoint[];
  };
}
