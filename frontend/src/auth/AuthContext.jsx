import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, setToken, setUnauthorizedHandler } from "../api/client";

const STORAGE_KEY = "hms.session";

const AuthContext = createContext(null);

function readSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      return null;
    }

    const session = JSON.parse(raw);

    if (!session?.token || !session?.user) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }

    // Important: set the token synchronously while restoring the session.
    setToken(session.token);

    return session;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    setToken("");
    return null;
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession);

  const user = session?.user || null;
  const roles = user?.roles || [];

  const logout = useCallback(() => {
    setToken("");
    localStorage.removeItem(STORAGE_KEY);
    setSession(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);

    return () => {
      setUnauthorizedHandler(() => {});
    };
  }, [logout]);

  const login = useCallback((data) => {
    const token = data?.access_token || "";
    const nextSession = {
      token,
      user: data?.user || null,
    };

    // Token must be set before anything else uses the API.
    setToken(token);

    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
  }, []);

  const refreshUser = useCallback(async () => {
    const freshUser = await api.get("/auth/me");

    setSession((current) => {
      if (!current) {
        return current;
      }

      const nextSession = {
        ...current,
        user: freshUser,
      };

      localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));

      return nextSession;
    });

    return freshUser;
  }, []);

  const hasRole = useCallback(
    (...allowedRoles) => allowedRoles.some((role) => roles.includes(role)),
    [roles],
  );

  const value = useMemo(
    () => ({
      user,
      login,
      logout,
      refreshUser,
      hasRole,
      isGuest: roles.includes("ROLE_CUSTOMER"),
      isOps: roles.some((role) =>
        ["ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"].includes(role),
      ),
      isManagement: roles.some((role) =>
        ["ROLE_ADMIN", "ROLE_MANAGER"].includes(role),
      ),
    }),
    [user, login, logout, refreshUser, hasRole, roles],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
