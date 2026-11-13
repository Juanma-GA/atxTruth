// Minimal API client for verification scripts (Node fetch, Bearer token).
export function apiClient(baseUrl) {
  async function call(method, path, { token, body } = {}) {
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(`${baseUrl}${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }
    return { status: response.status, json };
  }
  return {
    call,
    async login(email, password) {
      const r = await call('POST', '/api/auth/login', { body: { email, password } });
      if (r.status !== 200) throw new Error(`login ${email} → ${r.status} ${JSON.stringify(r.json)}`);
      return r.json.access_token;
    },
  };
}
