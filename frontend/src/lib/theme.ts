export type ThemePreference = 'system' | 'light' | 'dark';

/** `system` follows prefers-color-scheme (no attribute); light/dark pin it. */
export function applyTheme(theme: ThemePreference): void {
  const root = document.documentElement;
  if (theme === 'system') delete root.dataset.theme;
  else root.dataset.theme = theme;
}
