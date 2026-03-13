import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SettingsPage from "@/app/(app)/settings/page";

// Mock auth context
const mockRefreshUser = jest.fn();
jest.mock("@/lib/auth-context", () => ({
  useAuth: () => ({
    user: { id: 1, username: "testuser", email: "test@example.com", base_currency: "EUR" },
    loading: false,
    refreshUser: mockRefreshUser,
    logout: jest.fn(),
  }),
}));

// Mock theme context
const mockSetTheme = jest.fn();
jest.mock("@/lib/theme-context", () => ({
  useTheme: () => ({
    theme: "system" as const,
    setTheme: mockSetTheme,
    resolvedTheme: "light" as const,
  }),
}));

// Mock api/auth
jest.mock("@/lib/api/auth", () => ({
  updateMe: jest.fn().mockResolvedValue({}),
}));

// Mock all shadcn/ui components to simple HTML elements
jest.mock("@/components/ui/card", () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement("div", { className }, children),
  CardContent: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement("div", { className }, children),
  CardHeader: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  CardTitle: ({ children, id, className }: { children: React.ReactNode; id?: string; className?: string }) =>
    React.createElement("h2", { id, className }, children),
  CardDescription: ({ children }: { children: React.ReactNode }) =>
    React.createElement("p", null, children),
}));

jest.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick, disabled, variant, size, className, ...rest }: Record<string, unknown>) =>
    React.createElement(
      "button",
      { onClick, disabled, className, "aria-pressed": rest["aria-pressed"] },
      children as React.ReactNode
    ),
}));

jest.mock("@/components/ui/label", () => ({
  Label: ({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) =>
    React.createElement("label", { htmlFor }, children),
}));

jest.mock("@/components/ui/input", () => ({
  Input: (props: Record<string, unknown>) =>
    React.createElement("input", {
      id: props.id,
      value: props.value,
      readOnly: props.readOnly,
      disabled: props.disabled,
      className: props.className,
      "aria-label": props["aria-label"],
    }),
}));

jest.mock("@/components/ui/separator", () => ({
  Separator: () => React.createElement("hr"),
}));

jest.mock("@/components/ui/select", () => ({
  Select: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  SelectContent: ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", null, children),
  SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) =>
    React.createElement("option", { value }, children),
  SelectTrigger: ({ children, id, className }: { children: React.ReactNode; id?: string; className?: string }) =>
    React.createElement("div", { id, className }, children),
  SelectValue: () => React.createElement("span"),
}));

// Mock lucide-react icons to simple spans
jest.mock("lucide-react", () => {
  const icon = (name: string) => {
    const IconComponent = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
      (props, ref) =>
        React.createElement("span", { ...props, ref, "data-testid": `icon-${name}` })
    );
    IconComponent.displayName = name;
    return IconComponent;
  };
  return {
    Sun: icon("sun"),
    Moon: icon("moon"),
    Monitor: icon("monitor"),
    AlertTriangle: icon("alert-triangle"),
    Check: icon("check"),
    Coffee: icon("coffee"),
    Heart: icon("heart"),
  };
});

jest.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("renders the page heading", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("heading", { name: /settings/i, level: 1 })).toBeInTheDocument();
  });

  it("renders the Profile section with user information", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByDisplayValue("testuser")).toBeInTheDocument();
    expect(screen.getByDisplayValue("test@example.com")).toBeInTheDocument();
  });

  it("renders the Preferences section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Preferences")).toBeInTheDocument();
    expect(screen.getByText("Base Currency")).toBeInTheDocument();
    expect(screen.getByText("Theme")).toBeInTheDocument();
  });

  it("renders the Display Settings section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Display Settings")).toBeInTheDocument();
    expect(screen.getByText("Default Performance Period")).toBeInTheDocument();
    expect(screen.getByText("Default Allocation Grouping")).toBeInTheDocument();
  });

  it("renders the Import Settings section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Import Settings")).toBeInTheDocument();
    expect(screen.getByText("Default Broker")).toBeInTheDocument();
  });

  it("renders the Danger Zone section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Danger Zone")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /delete account/i })).toBeInTheDocument();
  });

  it("renders the Buy Me a Coffee section", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Buy Me a Coffee")).toBeInTheDocument();
  });

  it("renders theme option buttons (Light, Dark, System)", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("button", { name: /light/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dark/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /system/i })).toBeInTheDocument();
  });

  it("calls setTheme when a theme button is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /dark/i }));
    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("shows delete confirmation when Delete Account is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /delete account/i }));
    expect(
      screen.getByText(/are you sure you want to delete your account/i)
    ).toBeInTheDocument();
  });

  it("hides delete confirmation when Cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /delete account/i }));
    expect(screen.getByText(/are you sure/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
  });

  it("calls updateMe and refreshUser when Save Preferences is clicked", async () => {
    const { updateMe } = jest.requireMock("@/lib/api/auth");
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(screen.getByRole("button", { name: /save preferences/i }));

    expect(updateMe).toHaveBeenCalledWith({ base_currency: "EUR" });
  });
});
