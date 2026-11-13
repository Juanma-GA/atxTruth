import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

import { api } from '@/services/api';
import { errorMessage } from '@/services/apiErrors';
import { queryKeys } from '@/services/queryKeys';
import { useAuthStore } from '@/stores/auth';
import type { Me } from '@/types/api';

export function useMe() {
  const status = useAuthStore((s) => s.status);
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: () => api.get<Me>('/api/auth/me'),
    enabled: status === 'authenticated',
    staleTime: Infinity,
  });
}

export type MePatch = Partial<Pick<Me, 'display_name' | 'preferred_language' | 'theme'>>;

/**
 * HR20: the change is applied to the cached account at once (language and theme switch
 * immediately), saved in the background and rolled back with a message if the server rejects it.
 */
export function useUpdateMe() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (patch: MePatch) => api.patch<Me>('/api/auth/me', patch),
    onMutate: async (patch) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.me });
      const previous = queryClient.getQueryData<Me>(queryKeys.me);
      if (previous) queryClient.setQueryData<Me>(queryKeys.me, { ...previous, ...patch });
      return { previous };
    },
    onError: (error, _patch, context) => {
      if (context?.previous) queryClient.setQueryData(queryKeys.me, context.previous);
      toast.error(errorMessage(t, error));
    },
    onSuccess: (me) => queryClient.setQueryData(queryKeys.me, me),
  });
}
