import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChartToolbar, type ViewType, type IndicatorState } from "@/components/charts/chart-toolbar";

// Mock shadcn/ui Button component to a simple HTML button element
jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, className, ...rest }: Record<string, unknown>) =>
    React.createElement(
      "button",
      { onClick, disabled, className, "aria-pressed": rest["aria-pressed"] },
      children as React.ReactNode
    ),
}));

const defaultProps = {
  period: "6M",
  onPeriodChange: jest.fn(),
  viewType: "Candlestick" as ViewType,
  onViewTypeChange: jest.fn(),
  indicators: { sma20: true, sma50: true, rsi: false } as IndicatorState,
  onIndicatorsChange: jest.fn(),
};

describe("ChartToolbar", () => {
  beforeEach(() => jest.clearAllMocks());

  it("renders all period buttons", () => {
    render(<ChartToolbar {...defaultProps} />);
    for (const p of ["1D", "1W", "1M", "3M", "6M", "1Y", "ALL"]) {
      expect(screen.getByRole("button", { name: p })).toBeInTheDocument();
    }
  });

  it("renders view toggle buttons", () => {
    render(<ChartToolbar {...defaultProps} />);
    expect(screen.getByRole("button", { name: "Candlestick" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Line" })).toBeInTheDocument();
  });

  it("renders indicator checkboxes with correct state", () => {
    render(<ChartToolbar {...defaultProps} />);
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).toBeChecked();
    expect(checkboxes[2]).not.toBeChecked();
  });

  it("calls onPeriodChange when period button clicked", async () => {
    render(<ChartToolbar {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "1M" }));
    expect(defaultProps.onPeriodChange).toHaveBeenCalledWith("1M");
  });

  it("calls onViewTypeChange when view button clicked", async () => {
    render(<ChartToolbar {...defaultProps} />);
    await userEvent.click(screen.getByRole("button", { name: "Line" }));
    expect(defaultProps.onViewTypeChange).toHaveBeenCalledWith("Line");
  });

  it("calls onIndicatorsChange when checkbox toggled", async () => {
    render(<ChartToolbar {...defaultProps} />);
    const rsiCheckbox = screen.getAllByRole("checkbox")[2];
    await userEvent.click(rsiCheckbox);
    expect(defaultProps.onIndicatorsChange).toHaveBeenCalledWith({
      sma20: true,
      sma50: true,
      rsi: true,
    });
  });
});
