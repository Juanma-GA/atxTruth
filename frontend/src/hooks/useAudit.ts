import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { api } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type { AuditPage } from '@/types/api';

export function useAudit(page: number, pageSize: number, action: string) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (action) params.set('action', action);
  return useQuery({
    queryKey: queryKeys.audit(page, pageSize, action),
    queryFn: () => api.get<AuditPage>(`/api/audit?${params.toString()}`),
    placeholderData: keepPreviousData,
  });
}
