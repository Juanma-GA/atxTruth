import type { Setting } from '@/types/api';

/** Client-side check mirroring the backend rules; the server stays authoritative. */
export function localViolation(
  type: Setting['value_type'],
  rules: { min?: number; max?: number; min_length?: number; max_length?: number },
  value: unknown,
): { key: string; params: Record<string, unknown> } | null {
  if (type === 'integer' || type === 'number') {
    if (typeof value !== 'number' || Number.isNaN(value) || (type === 'integer' && !Number.isInteger(value)))
      return { key: 'errors.settings.invalid_type', params: {} };
    if (rules.min !== undefined && value < rules.min) return { key: 'errors.settings.too_small', params: { min: rules.min } };
    if (rules.max !== undefined && value > rules.max) return { key: 'errors.settings.too_large', params: { max: rules.max } };
  }
  if (type === 'string' && typeof value === 'string') {
    if (rules.min_length !== undefined && value.trim().length < rules.min_length)
      return { key: 'errors.settings.too_short', params: { min_length: rules.min_length } };
    if (rules.max_length !== undefined && value.length > rules.max_length)
      return { key: 'errors.settings.too_long', params: { max_length: rules.max_length } };
  }
  return null;
}
