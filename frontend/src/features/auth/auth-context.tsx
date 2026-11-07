"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  clearAccessToken,
  refreshAccessToken,
  setRefreshFailureHandler,
} from "@/lib/api-client";

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

interface AuthContextValue {
  /**
   * True once the bootstrap refresh attempt has settled (success or failure).
   * Gate protected data fetches and route guards on this flag.
   */
  isReady: boolean;
  /**
   * True when a valid access token is held in memory after a successful
   * bootstrap refresh. False after the refresh fails or the user logs out.
   */
  isAuthenticated: boolean;
  /**
   * Call after a successful login/verify-email so the context reflects the
   * new authenticated state without requiring another network round-trip.
   */
  onLoginSuccess: () => void;
  /**
   * Clears the in-memory token and redirects to /login.
   */
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Avoid double-bootstrapping in React Strict Mode.
  const bootstrapped = useRef(false);

  const logout = useCallback(() => {
    clearAccessToken();
    setIsAuthenticated(false);
    router.push("/login");
  }, [router]);

  // Register the failure handler on the api-client so the 401 interceptor can
  // trigger a redirect without importing the router itself.
  useEffect(() => {
    setRefreshFailureHandler(logout);
  }, [logout]);

  // Bootstrap: attempt a silent refresh using the HttpOnly refresh cookie.
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;

    refreshAccessToken()
      .then(() => {
        setIsAuthenticated(true);
      })
      .catch(() => {
        // No valid session — stay unauthenticated. The api-client's failure
        // handler will redirect to /login if a protected request is attempted.
        setIsAuthenticated(false);
      })
      .finally(() => {
        setIsReady(true);
      });
  }, []);

  const onLoginSuccess = useCallback(() => {
    setIsAuthenticated(true);
  }, []);

  return (
    <AuthContext.Provider
      value={{ isReady, isAuthenticated, onLoginSuccess, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
