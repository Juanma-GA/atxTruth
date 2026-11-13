import { create } from 'zustand';

/**
 * The access token lives only in memory (HR1); the refresh token is an HttpOnly cookie the
 * browser sends to /api/auth. `status` drives which part of the app is shown.
 */
export type AuthStatus = 'checking' | 'anonymous' | 'authenticated';

interface AuthState {
  accessToken: string | null;
  status: AuthStatus;
  setSession: (token: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  status: 'checking',
  setSession: (token) => set({ accessToken: token, status: 'authenticated' }),
  clear: () => set({ accessToken: null, status: 'anonymous' }),
}));
