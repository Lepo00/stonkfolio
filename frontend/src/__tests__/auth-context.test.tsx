import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "@/lib/auth-context";

// Mock the API module
const mockGetMe = jest.fn();
const mockApiLogout = jest.fn();

jest.mock("@/lib/api/auth", () => ({
  getMe: (...args: unknown[]) => mockGetMe(...args),
  logout: (...args: unknown[]) => mockApiLogout(...args),
}));

const testUser = {
  id: 1,
  username: "testuser",
  email: "test@example.com",
  base_currency: "EUR",
};

// A helper component that exposes auth context for testing
function AuthConsumer() {
  const { user, loading, refreshUser, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? JSON.stringify(user) : "null"}</span>
      <button onClick={refreshUser}>Refresh</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it("throws when useAuth is used outside AuthProvider", () => {
    // Suppress console.error for the expected error
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<AuthConsumer />)).toThrow(
      "useAuth must be used within AuthProvider"
    );
    spy.mockRestore();
  });

  it("fetches user on mount and sets user when successful", async () => {
    mockGetMe.mockResolvedValueOnce(testUser);

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    // Initially loading
    expect(screen.getByTestId("loading").textContent).toBe("true");

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    expect(screen.getByTestId("user").textContent).toBe(JSON.stringify(testUser));
    expect(mockGetMe).toHaveBeenCalledTimes(1);
  });

  it("sets user to null when getMe fails", async () => {
    mockGetMe.mockRejectedValueOnce(new Error("Unauthorized"));

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    expect(screen.getByTestId("user").textContent).toBe("null");
  });

  it("refreshUser fetches user again", async () => {
    mockGetMe.mockResolvedValueOnce(testUser);

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const updatedUser = { ...testUser, username: "updateduser" };
    mockGetMe.mockResolvedValueOnce(updatedUser);

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe(JSON.stringify(updatedUser));
    });

    expect(mockGetMe).toHaveBeenCalledTimes(2);
  });

  it("logout clears user and calls apiLogout", async () => {
    mockGetMe.mockResolvedValueOnce(testUser);

    render(
      <AuthProvider>
        <AuthConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe(JSON.stringify(testUser));
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /logout/i }));

    expect(mockApiLogout).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("user").textContent).toBe("null");
  });
});
