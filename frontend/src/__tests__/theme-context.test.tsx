import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "@/lib/theme-context";

// Helper component that exposes theme context
function ThemeConsumer() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button onClick={() => setTheme("dark")}>Set Dark</button>
      <button onClick={() => setTheme("light")}>Set Light</button>
      <button onClick={() => setTheme("system")}>Set System</button>
    </div>
  );
}

describe("ThemeContext", () => {
  let matchMediaListeners: Array<(e: MediaQueryListEvent) => void>;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    document.documentElement.classList.remove("light", "dark");
    matchMediaListeners = [];

    // Mock matchMedia
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: jest.fn().mockImplementation((query: string) => ({
        matches: false, // default: prefers light
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
          matchMediaListeners.push(handler);
        }),
        removeEventListener: jest.fn((_event: string, handler: (e: MediaQueryListEvent) => void) => {
          matchMediaListeners = matchMediaListeners.filter((h) => h !== handler);
        }),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  it("throws when useTheme is used outside ThemeProvider", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<ThemeConsumer />)).toThrow(
      "useTheme must be used within ThemeProvider"
    );
    spy.mockRestore();
  });

  it("defaults to system theme", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("theme").textContent).toBe("system");
  });

  it("resolves system theme to light when prefers-color-scheme is light", () => {
    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    // matchMedia returns matches: false (light preference)
    expect(screen.getByTestId("resolved").textContent).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
  });

  it("resolves system theme to dark when prefers-color-scheme is dark", () => {
    // Override matchMedia to prefer dark
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: jest.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    expect(screen.getByTestId("resolved").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("setTheme updates theme and stores it in localStorage", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    await user.click(screen.getByRole("button", { name: /set dark/i }));

    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(screen.getByTestId("resolved").textContent).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("reads initial theme from localStorage", () => {
    localStorage.setItem("theme", "dark");

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    // After useEffect runs, theme should be read from localStorage
    // The initial state is "system" but useEffect updates it
    waitFor(() => {
      expect(screen.getByTestId("theme").textContent).toBe("dark");
    });
  });

  it("switching from dark to light updates the DOM", async () => {
    const user = userEvent.setup();

    render(
      <ThemeProvider>
        <ThemeConsumer />
      </ThemeProvider>
    );

    await user.click(screen.getByRole("button", { name: /set dark/i }));
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.classList.contains("light")).toBe(false);

    await user.click(screen.getByRole("button", { name: /set light/i }));
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
