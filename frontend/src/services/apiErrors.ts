import i18n, { type TFunction } from 'i18next';

/** An API failure: `code` + `params` from the backend error contract, or a network failure. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly params: Record<string, unknown>;

  constructor(status: number, code: string, params: Record<string, unknown> = {}) {
    super(code);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.params = params;
  }

  get isNetwork(): boolean {
    return this.status === 0;
  }
}

export function networkError(): ApiError {
  return new ApiError(0, 'network');
}

export async function apiErrorFromResponse(response: Response): Promise<ApiError> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'error' in body) {
      const error = (body as { error: { code?: unknown; params?: unknown } }).error;
      if (typeof error.code === 'string') {
        const params = error.params && typeof error.params === 'object' ? (error.params as Record<string, unknown>) : {};
        return new ApiError(response.status, error.code, params);
      }
    }
  } catch {
    // Not JSON (e.g. a proxy error page): reported below by status only.
  }
  return new ApiError(response.status, response.status >= 500 ? 'server.internal' : `http.${response.status}`);
}

/**
 * Makes error parameters readable (HR21): lists are joined, language codes and field states are
 * translated. Codes of data (S1.1.1, sector) stay as they are: they are identifiers the user knows.
 */
export function formatParams(t: TFunction, params: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    if (key === 'languages' && Array.isArray(value)) {
      out[key] = value.map((lang) => t(`languages.short.${String(lang)}`, { defaultValue: String(lang) })).join(', ');
    } else if (key === 'state' && typeof value === 'string') {
      out[key] = t(`fieldState.${value}`);
    } else if (Array.isArray(value)) {
      out[key] = value.join(', ');
    } else {
      out[key] = value;
    }
  }
  return out;
}

/** Translates an error code with its parameters; an unknown code gets a generic sentence. */
export function codeMessage(t: TFunction, code: string, params: Record<string, unknown> = {}): string {
  const key = `errors.${code}`;
  const formatted = formatParams(t, { ref: '—', ...params });
  return i18n.exists(key) ? t(key, formatted) : t('errors.unknown', formatted);
}

/** The sentence to show the user for an error, always through i18n (HR15). */
export function errorMessage(t: TFunction, error: unknown): string {
  if (!(error instanceof ApiError)) return t('errors.unexpected');
  if (error.isNetwork) return t('errors.network');
  return codeMessage(t, error.code, error.params);
}
