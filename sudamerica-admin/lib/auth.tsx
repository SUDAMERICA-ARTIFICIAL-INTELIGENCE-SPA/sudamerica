"use client";

import { auth } from "@/lib/firebase";
import { ApiError, api, clearTokens } from "@/lib/api";
import type { AuthState, AuthTokens, Usuario } from "@/lib/types";
import {
  signInWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";
import { useRouter } from "next/navigation";
import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface LoginCredentials {
  email: string;
  password: string;
}

interface AuthContextValue extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, tokens: null });
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // On mount, listen for Firebase auth state and exchange token for backend JWT
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        clearTokens();
        setState({ user: null, tokens: null });
        setIsLoading(false);
        return;
      }

      // Check if we already have a valid backend JWT
      const stored = localStorage.getItem("admin_access_token");
      if (stored) {
        try {
          const user = await api.get<Usuario>("/auth/me", {
            useAuthPath: true,
          });
          const tokens: AuthTokens = {
            access_token: stored,
            refresh_token: localStorage.getItem("admin_refresh_token") || "",
          };
          setState({ user, tokens });
        } catch {
          clearTokens();
          setState({ user: null, tokens: null });
        }
      }
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      // 1. Sign in with Firebase
      const userCredential = await signInWithEmailAndPassword(
        auth,
        credentials.email,
        credentials.password,
      );

      // 2. Get Firebase ID token
      const firebaseToken = await userCredential.user.getIdToken();

      // 3. Exchange Firebase token for backend JWT
      const result = await api.post<AuthTokens>(
        "/auth/firebase-login",
        { firebase_token: firebaseToken },
        { skipAuth: true, useAuthPath: true },
      );

      // 4. Store backend tokens
      localStorage.setItem("admin_access_token", result.access_token);
      localStorage.setItem("admin_refresh_token", result.refresh_token);

      // 5. Fetch user profile
      const user = await api.get<Usuario>("/auth/me", { useAuthPath: true });

      if (user.role !== "SUPERADMIN") {
        clearTokens();
        await signOut(auth);
        throw new ApiError(403, "Acceso restringido a SUPERADMIN");
      }

      setState({ user, tokens: result });
      router.push("/");
    },
    [router],
  );

  const logout = useCallback(async () => {
    clearTokens();
    await signOut(auth);
    setState({ user: null, tokens: null });
    router.push("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      logout,
      isAuthenticated: state.user !== null,
      isLoading,
    }),
    [state, login, logout, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) return null;
  return <>{children}</>;
}
