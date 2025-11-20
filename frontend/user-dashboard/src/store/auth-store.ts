import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types/auth';

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token) => set({ token }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'med--ai-saas-auth',
    }
  )
);
