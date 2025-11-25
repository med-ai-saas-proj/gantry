import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  setAuth: (token: string, refreshToken: string, expiresIn: number) => void;
  setToken: (token: string, expiresIn: number) => void;
  logout: () => void;
  isTokenExpired: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      expiresAt: null,
      setAuth: (token, refreshToken, expiresIn) =>
        set({
          token,
          refreshToken,
          expiresAt: Date.now() + expiresIn * 1000,
        }),
      setToken: (token, expiresIn) =>
        set({
          token,
          expiresAt: Date.now() + expiresIn * 1000,
        }),
      logout: () => set({ token: null, refreshToken: null, expiresAt: null }),
      isTokenExpired: () => {
        const expiresAt = get().expiresAt;
        if (!expiresAt) return true;
        // Consider token expired if within 1 minute of expiry
        return Date.now() >= expiresAt - 60000;
      },
    }),
    {
      name: 'med--ai-saas-auth',
    }
  )
);
