import { describe, expect, it } from 'vitest';

import { deepMerge } from '@/hooks/useSettings';
import { localViolation } from '@/lib/settingValidation';

describe('setting validation mirrors the backend', () => {
  it('checks numeric ranges and integer type', () => {
    expect(localViolation('integer', { min: 5, max: 200 }, 4)?.key).toBe('errors.settings.too_small');
    expect(localViolation('integer', { min: 5, max: 200 }, 201)?.key).toBe('errors.settings.too_large');
    expect(localViolation('integer', {}, 2.5)?.key).toBe('errors.settings.invalid_type');
    expect(localViolation('number', {}, Number.NaN)?.key).toBe('errors.settings.invalid_type');
    expect(localViolation('number', { min: 0.1 }, 0.5)).toBeNull();
  });

  it('checks string lengths', () => {
    expect(localViolation('string', { min_length: 1 }, '  ')?.key).toBe('errors.settings.too_short');
    expect(localViolation('string', { max_length: 3 }, 'abcd')?.key).toBe('errors.settings.too_long');
  });
});

describe('deepMerge (HR10)', () => {
  it('keeps nested keys', () => {
    expect(deepMerge({ a: { b: 1, c: 2 }, d: 3 }, { a: { c: 9 } })).toEqual({ a: { b: 1, c: 9 }, d: 3 });
  });
});
