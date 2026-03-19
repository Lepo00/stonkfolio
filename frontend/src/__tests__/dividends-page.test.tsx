import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePortfolio } from "@/lib/portfolio-context";
import { getDividends } from "@/lib/api/portfolios";

jest.mock("@/lib/portfolio-context");
jest.mock("@/lib/api/portfolios");
// Mock recharts to avoid canvas issues in jsdom
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

import DividendsPage from "@/app/(app)/dividends/page";

const mockPortfolio = { id: 1, name: "Main", created_at: "2025-01-01" };

const mockDividendData = {
  summary: {
    total_dividends_12m: "130.00",
    total_dividends_all_time: "200.00",
    trailing_yield_pct: "2.50",
    monthly_average_12m: "10.83",
    dividend_holding_count: 2,
    total_holding_count: 5,
  },
  monthly_history: Array.from({ length: 24 }, (_, i) => ({
    month: `2026-${String(3 - Math.floor(i / 1)).padStart(2, "0")}`,
    amount: i === 0 ? "50.00" : "0.00",
  })),
  by_instrument: [
    {
      instrument_name: "Apple Inc",
      ticker: "AAPL",
      total_12m: "100.00",
      pct_of_total: "76.9",
      payment_count_12m: 4,
    },
    {
      instrument_name: "Microsoft Corp",
      ticker: "MSFT",
      total_12m: "30.00",
      pct_of_total: "23.1",
      payment_count_12m: 2,
    },
  ],
  recent_payments: [
    { date: "2026-03-15", instrument_name: "Apple Inc", ticker: "AAPL", amount: "25.00" },
    { date: "2026-02-15", instrument_name: "Microsoft Corp", ticker: "MSFT", amount: "15.00" },
  ],
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("DividendsPage", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows empty state when no portfolio is selected", () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: null });
    renderWithProviders(<DividendsPage />);
    expect(screen.getByText("Select a portfolio to view dividend data.")).toBeInTheDocument();
  });

  it("renders summary cards with data", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect(await screen.findByText("Income (12M)")).toBeInTheDocument();
    expect(screen.getByText("Trailing Yield")).toBeInTheDocument();
    expect(screen.getByText("Monthly Average")).toBeInTheDocument();
    expect(screen.getByText("Dividend Holdings")).toBeInTheDocument();
    expect(screen.getByText("2.50%")).toBeInTheDocument();
  });

  it("renders by-instrument table", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect((await screen.findAllByText("Apple Inc")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Microsoft Corp").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("76.9%")).toBeInTheDocument();
  });

  it("renders recent payments", async () => {
    (usePortfolio as jest.Mock).mockReturnValue({ selected: mockPortfolio });
    (getDividends as jest.Mock).mockResolvedValue(mockDividendData);
    renderWithProviders(<DividendsPage />);

    expect(await screen.findByText("2026-03-15")).toBeInTheDocument();
    expect(screen.getByText("2026-02-15")).toBeInTheDocument();
  });
});
