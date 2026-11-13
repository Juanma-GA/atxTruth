export const queryKeys = {
  publicConfig: ['publicConfig'] as const,
  clientConfig: ['clientConfig'] as const,
  me: ['me'] as const,
  settings: ['settings'] as const,
  infrastructure: ['settings', 'infrastructure'] as const,
  users: (includeDeleted: boolean) => ['users', { includeDeleted }] as const,
  usersAll: ['users'] as const,
  audit: (page: number, pageSize: number, action: string) => ['audit', { page, pageSize, action }] as const,
};
