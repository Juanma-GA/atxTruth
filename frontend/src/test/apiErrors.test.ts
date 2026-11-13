import { describe, expect, it } from 'vitest';

import i18n from '@/i18n';
import { ApiError, apiErrorFromResponse, errorMessage } from '@/services/apiErrors';

const t = i18n.getFixedT('es');

describe('API errors are translated, never shown raw (HR15/HR21)', () => {
  it('reads the error contract and translates code + params', async () => {
    const response = new Response(
      JSON.stringify({ error: { code: 'auth.too_many_attempts', params: { minutes: 15 } } }),
      { status: 429 },
    );
    const error = await apiErrorFromResponse(response);
    expect(error.code).toBe('auth.too_many_attempts');
    expect(errorMessage(t, error)).toBe('Demasiados intentos fallidos. Vuelve a probar dentro de 15 minutos.');
  });

  it('falls back to a generic sentence for an unknown code', () => {
    expect(errorMessage(t, new ApiError(400, 'something.new', { ref: 'abc' }))).toBe('Algo ha fallado. Referencia: abc');
  });

  it('reports network failures as such', () => {
    expect(errorMessage(t, new ApiError(0, 'network'))).toContain('El servidor no responde');
  });

  it('handles non-JSON error bodies', async () => {
    const error = await apiErrorFromResponse(new Response('<html>bad gateway</html>', { status: 502 }));
    expect(error.code).toBe('server.internal');
  });
});
