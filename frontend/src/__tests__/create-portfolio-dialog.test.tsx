import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CreatePortfolioDialog } from "@/components/portfolios/create-portfolio-dialog";

// Mock dependencies
const mockSetSelected = jest.fn();
const mockRefreshPortfolios = jest.fn().mockResolvedValue(undefined);

jest.mock("@/lib/portfolio-context", () => ({
  usePortfolio: () => ({
    portfolios: [],
    selected: null,
    setSelected: mockSetSelected,
    refreshPortfolios: mockRefreshPortfolios,
  }),
}));

const mockMutate = jest.fn();
let mockMutationState = { isPending: false };

jest.mock("@tanstack/react-query", () => ({
  useMutation: ({ mutationFn, onSuccess, onError }: {
    mutationFn: (name: string) => Promise<unknown>;
    onSuccess: (data: unknown) => void;
    onError: (err: Error) => void;
  }) => ({
    mutate: (name: string) => {
      mockMutate(name);
      mutationFn(name).then(onSuccess).catch(onError);
    },
    ...mockMutationState,
  }),
}));

jest.mock("@/lib/api/portfolios", () => ({
  createPortfolio: jest.fn().mockResolvedValue({ id: 1, name: "Test", created_at: "2026-01-01" }),
}));

// Mock UI components for testing
jest.mock("@/components/ui/label", () => ({
  Label: ({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) =>
    React.createElement("label", { htmlFor }, children),
}));

jest.mock("@/components/ui/input", () => ({
  Input: (props: React.ComponentProps<"input">) =>
    React.createElement("input", props),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, type }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    type?: "button" | "submit" | "reset";
  }) =>
    React.createElement("button", { onClick, disabled, type }, children),
}));

jest.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe("CreatePortfolioDialog", () => {
  const onOpenChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockMutationState = { isPending: false };
  });

  it("renders dialog content when open", () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    expect(screen.getByText("Create portfolio")).toBeInTheDocument();
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<CreatePortfolioDialog open={false} onOpenChange={onOpenChange} />);
    expect(screen.queryByText("Create portfolio")).not.toBeInTheDocument();
  });

  it("disables submit when name is empty", () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).toBeDisabled();
  });

  it("disables submit when name is whitespace only", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "   ");
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).toBeDisabled();
  });

  it("enables submit when name has content", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "My Portfolio");
    const submitButton = screen.getByRole("button", { name: "Create" });
    expect(submitButton).not.toBeDisabled();
  });

  it("calls mutate on form submit", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "My Portfolio");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    expect(mockMutate).toHaveBeenCalledWith("My Portfolio");
  });

  it("calls cancel to close dialog", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("clears input when dialog reopens", () => {
    const { rerender } = render(
      <CreatePortfolioDialog open={false} onOpenChange={onOpenChange} />
    );
    rerender(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    expect(screen.getByLabelText("Name")).toHaveValue("");
  });

  it("on success: refreshes, selects, and closes", async () => {
    render(<CreatePortfolioDialog open={true} onOpenChange={onOpenChange} />);
    await userEvent.type(screen.getByLabelText("Name"), "Test");
    await userEvent.click(screen.getByRole("button", { name: "Create" }));
    await waitFor(() => {
      expect(mockRefreshPortfolios).toHaveBeenCalled();
      expect(mockSetSelected).toHaveBeenCalledWith({ id: 1, name: "Test", created_at: "2026-01-01" });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
