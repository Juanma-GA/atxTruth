import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';

import { api } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import { useAuthStore } from '@/stores/auth';
import type { Me } from '@/types/api';

export function useSignIn() {
  const queryClient = useQueryClient();
  return useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.post<{ access_token: string }>('/api/auth/login', { email, password });
      useAuthStore.getState().setSession(access_token);
      const me = await api.get<Me>('/api/auth/me');
      queryClient.setQueryData(queryKeys.me, me);
      return me;
    },
    [queryClient],
  );
}

export function useSignOut() {
  const queryClient = useQueryClient();
  return useCallback(async () => {
    try {
      await api.post('/api/auth/logout');
    } finally {
      useAuthStore.getState().clear();
      queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== queryKeys.publicConfig[0] });
    }
  }, [queryClient]);
}
