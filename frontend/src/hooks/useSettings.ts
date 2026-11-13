import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';

import { api } from '@/services/api';
import { errorMessage } from '@/services/apiErrors';
import { queryKeys } from '@/services/queryKeys';
import type { InfrastructureItem, Setting, SettingValue } from '@/types/api';

export function useSettings() {
  return useQuery({ queryKey: queryKeys.settings, queryFn: () => api.get<Setting[]>('/api/settings') });
}

export function useInfrastructure() {
  return useQuery({
    queryKey: queryKeys.infrastructure,
    queryFn: () => api.get<InfrastructureItem[]>('/api/settings/infrastructure'),
  });
}

/** Deep merge for nested objects (HR10), mirrored from the backend for the optimistic value. */
export function deepMerge(base: Record<string, unknown>, patch: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(patch)) {
    const current = result[key];
    result[key] =
      current && typeof current === 'object' && !Array.isArray(current) && value && typeof value === 'object' && !Array.isArray(value)
        ? deepMerge(current as Record<string, unknown>, value as Record<string, unknown>)
        : value;
  }
  return result;
}

interface UpdateVars {
  key: string;
  value?: SettingValue;
  reset?: boolean;
}

/** HR20: the new value shows at once; on a server rejection it rolls back and says why. */
export function useUpdateSetting(onRejected?: (key: string, message: string) => void) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: ({ key, value, reset }: UpdateVars) =>
      reset
        ? api.post<Setting>(`/api/settings/${encodeURIComponent(key)}/reset`)
        : api.patch<Setting>(`/api/settings/${encodeURIComponent(key)}`, { value }),
    onMutate: async ({ key, value, reset }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.settings });
      const previous = queryClient.getQueryData<Setting[]>(queryKeys.settings);
      if (previous) {
        queryClient.setQueryData<Setting[]>(
          queryKeys.settings,
          previous.map((s) => {
            if (s.key !== key) return s;
            if (reset) return { ...s, value: s.default_value };
            const next =
              s.value_type === 'object' && value && typeof value === 'object' && typeof s.value === 'object'
                ? deepMerge(s.value as Record<string, unknown>, value as Record<string, unknown>)
                : (value as SettingValue);
            return { ...s, value: next };
          }),
        );
      }
      return { previous };
    },
    onError: (error, vars, context) => {
      if (context?.previous) queryClient.setQueryData(queryKeys.settings, context.previous);
      const message = errorMessage(t, error);
      onRejected?.(vars.key, message);
      toast.error(message);
    },
    onSuccess: (setting) => {
      queryClient.setQueryData<Setting[]>(queryKeys.settings, (list) =>
        list?.map((s) => (s.key === setting.key ? setting : s)),
      );
      toast.success(t('config.saved'));
    },
    onSettled: () => {
      // Settings feed the rest of the UI (app name, default language, page size...).
      void queryClient.invalidateQueries({ queryKey: queryKeys.publicConfig });
      void queryClient.invalidateQueries({ queryKey: queryKeys.clientConfig });
    },
  });
}
