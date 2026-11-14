/** States of a field that are not values (mirrors backend app/core/field_state.py). */
export const FIELD_STATES = ['to_complete', 'not_applicable', 'none', 'unmapped'] as const;
export type FieldState = (typeof FIELD_STATES)[number];

export function isFieldState(value: unknown): value is FieldState {
  return typeof value === 'string' && (FIELD_STATES as readonly string[]).includes(value);
}
