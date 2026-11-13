/**
 * HR21: never render raw machine tokens. Used only as a last resort when there is no translation
 * for a token (translations always win): `to_review` → "To review", `in-scope` → "In scope".
 */
export function humanizeToken(token: string): string {
  const spaced = token
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_\-.]+/g, ' ')
    .trim()
    .toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
