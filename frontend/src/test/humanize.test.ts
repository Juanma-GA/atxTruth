import { describe, expect, it } from 'vitest';

import { humanizeToken } from '@/lib/humanize';

describe('humanizeToken (HR21)', () => {
  it.each([
    ['in_scope', 'In scope'],
    ['to-review', 'To review'],
    ['maxAttempts', 'Max attempts'],
    ['auth.login_failed', 'Auth login failed'],
    ['ADMIN', 'Admin'],
  ])('%s → %s', (input, expected) => {
    expect(humanizeToken(input)).toBe(expected);
  });
});
