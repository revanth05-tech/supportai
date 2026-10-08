"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

import {
  apiFetch,
  getApiErrorMessage,
  refreshAccessToken,
  setAccessToken,
  API_BASE,
} from "./api";

type User = {
  email: string;
  displayName: string | null;
};

type Tenant = {
  id: string;
  name: string;
  siteKey: string;
};

type CurrentAccount = {
  email: string;
  displayName: string | null;
  tenantId: string;
  tenantName: string;
  siteKey: string;
};

type AuthState = {
  user: User | null;
  tenant: Tenant | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    businessName: string,
    displayName?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  demoLogin: () => Promise<void>;
};

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(true);

  function applyAuth(data: { accessToken: string }) {
    setAccessToken(data.accessToken);
  }

  async function getCurrentAccount(): Promise<CurrentAccount> {
    const me = await apiFetch("/api/auth/me");

    if (!me.ok) {
      throw new Error("Failed to load account details.");
    }

    return (await me.json()) as CurrentAccount;
  }

  function applyCurrentAccount(account: CurrentAccount) {
    setUser({
      email: account.email,
      displayName: account.displayName,
    });

    setTenant({
      id: account.tenantId,
      name: account.tenantName,
      siteKey: account.siteKey,
    });
  }

  async function loadCurrentUser() {
    applyCurrentAccount(await getCurrentAccount());
  }

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const token = await refreshAccessToken();

      if (token && !cancelled) {
        try {
          const account = await getCurrentAccount();
          if (!cancelled) applyCurrentAccount(account);
        } catch {
          if (!cancelled) {
            setAccessToken(null);
            setUser(null);
            setTenant(null);
          }
        }
      }

      if (!cancelled) {
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  async function login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      throw new Error(await getApiErrorMessage(res, "Login failed"));
    }

    const data = await res.json();

    applyAuth(data);
    await loadCurrentUser();
  }

  async function register(
    email: string,
    password: string,
    businessName: string,
    displayName?: string,
  ) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        tenantName: businessName,
        displayName,
      }),
    });

    if (!res.ok) {
      throw new Error(await getApiErrorMessage(res, "Registration failed"));
    }

    const data = await res.json();

    applyAuth(data);
    await loadCurrentUser();
  }

  async function demoLogin() {
    const res = await fetch(`${API_BASE}/api/auth/demo-login`, {
      method: "POST",
      credentials: "include",
    });

    if (!res.ok) {
      throw new Error(await getApiErrorMessage(res, "Demo unavailable"));
    }

    const data = await res.json();

    applyAuth(data);
    await loadCurrentUser();
  }

  async function logout() {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    });

    setAccessToken(null);
    setUser(null);
    setTenant(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        tenant,
        loading,
        login,
        register,
        logout,
        demoLogin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return ctx;
}
