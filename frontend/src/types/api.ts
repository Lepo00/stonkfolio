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
  twr_return_pct: string | null;
  xirr_return_pct: string | null;
  benchmark_return_pct: string | null;
}

export interface PerformanceSeries {
  series: { date: string; value: string }[];
  benchmark_series: { date: string; value: string }[] | null;
  benchmark_name: string | null;
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

export interface AdviceItem {
  rule_id: string;
  category: "risk" | "performance" | "diversification" | "cost" | "income" | "technical" | "behavioral" | "health";
  priority: "critical" | "warning" | "info" | "positive";
  title: string;
  message: string;
  holdings: string[];
  metadata: Record<string, unknown>;
}

export interface AdviceResponse {
  items: AdviceItem[];
  has_pending_analysis: boolean;
  disclaimer: string;
}

export interface SuggestedETF {
  name: string;
  ticker: string;
  isin: string;
  provider: string;
  ter: string;
  index_tracked: string;
  why: string;
}

export interface Recommendation {
  category: string;
  title: string;
  rationale: string;
  suggested_etfs: SuggestedETF[];
  impact: string;
  confidence: "high" | "medium" | "low";
  priority: number;
}

export interface HealthScore {
  overall_score: number;
  summary: string;
  sub_scores: Record<string, { score: number; weight: number; item_count: number }>;
}

export interface TopAction {
  action: string;
  rationale: string;
  impact: string;
  urgency: "urgent" | "recommended" | "consider";
  related_rule_id: string;
  related_holdings: string[];
}

export interface Scenario {
  title: string;
  description: string;
  before: {
    allocation: Record<string, number>;
    metrics: Record<string, number>;
  };
  after: {
    allocation: Record<string, number>;
    metrics: Record<string, number>;
  };
}

export interface FullAdviceResponse {
  health_score: HealthScore;
  top_actions: TopAction[];
  recommendations: Recommendation[];
  scenarios: Scenario[];
  advice_items: AdviceItem[];
  has_pending_analysis: boolean;
  disclaimer: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface DividendSummary {
  total_dividends_12m: string;
  total_dividends_all_time: string;
  trailing_yield_pct: string;
  monthly_average_12m: string;
  dividend_holding_count: number;
  total_holding_count: number;
}

export interface DividendMonthly {
  month: string;
  amount: string;
}

export interface DividendByInstrument {
  instrument_name: string;
  ticker: string;
  total_12m: string;
  pct_of_total: string;
  payment_count_12m: number;
}

export interface DividendPayment {
  date: string;
  instrument_name: string;
  ticker: string;
  amount: string;
}

export interface DividendResponse {
  summary: DividendSummary;
  monthly_history: DividendMonthly[];
  by_instrument: DividendByInstrument[];
  recent_payments: DividendPayment[];
}
