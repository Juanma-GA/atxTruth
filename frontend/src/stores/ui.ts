import { create } from 'zustand';

import type { Language } from '@/i18n';

/** UI-only, in-memory state. Nothing here is persisted in the browser (HR1). */
interface UiState {
  /** Language picked on the sign-in screen, before there is an account to store it in. */
  anonymousLanguage: Language | null;
  setAnonymousLanguage: (language: Language) => void;
}

export const useUiStore = create<UiState>((set) => ({
  anonymousLanguage: null,
  setAnonymousLanguage: (language) => set({ anonymousLanguage: language }),
}));
