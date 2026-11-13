/**
 * The single API client. Adds the in-memory access token; on a 401 it tries one silent refresh
 * through the HttpOnly cookie and retries once. Errors are ApiError (code + params), translated
 * by the UI.
 */
import { useAuthStore } from '@/stores/auth';

import { ApiError, apiErrorFromResponse, networkError } from './apiErrors';

type Listener = () => void;
let sessionExpiredListener: Listener = () => {};

export function onSessionExpired(listener: Listener): void {
  sessionExpiredListener = listener;
}

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  let response: Response;
  try {
    response = await fetch('/api/auth/refresh', { method: 'POST', credentials: 'same-origin' });
  } catch {
    throw networkError();
  }
  if (response.status >= 500) throw networkError();
  if (!response.ok) return false;
  const body = (await response.json()) as { access_token: string };
  useAuthStore.getState().setSession(body.access_token);
  return true;
}

/** true: a new access token is set. false: there is no session. Throws when the server is unreachable. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function send(path: string, init: RequestInit, retry: boolean): Promise<Response> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body !== undefined && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers, credentials: 'same-origin' });
  } catch {
    throw networkError();
  }
  if (response.status === 401 && retry && token) {
    if (await refreshSession()) return send(path, init, false);
    useAuthStore.getState().clear();
    sessionExpiredListener();
  }
  return response;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await send(path, init, true);
  if (!response.ok) throw await apiErrorFromResponse(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
};

export { ApiError };
