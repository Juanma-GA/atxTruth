import { useQuery } from '@tanstack/react-query';

import { api } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import { useAuthStore } from '@/stores/auth';
import type { ClientConfig, PublicConfig } from '@/types/api';

export function usePublicConfig() {
  return useQuery({ queryKey: queryKeys.publicConfig, queryFn: () => api.get<PublicConfig>('/api/public/config') });
}

export function useClientConfig(enabled = true) {
  const status = useAuthStore((s) => s.status);
  return useQuery({
    queryKey: queryKeys.clientConfig,
    queryFn: () => api.get<ClientConfig>('/api/config'),
    enabled: enabled && status === 'authenticated',
  });
}
