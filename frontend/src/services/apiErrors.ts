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

/** The sentence to show the user for an error, always through i18n (HR15). */
export function errorMessage(t: TFunction, error: unknown): string {
  if (!(error instanceof ApiError)) return t('errors.unexpected');
  if (error.isNetwork) return t('errors.network');
  const key = `errors.${error.code}`;
  const params = { ref: '—', ...error.params };
  return i18n.exists(key) ? t(key, params) : t('errors.unknown', params);
}
