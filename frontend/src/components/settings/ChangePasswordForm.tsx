import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Field } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { errorMessage } from '@/services/apiErrors';
import { queryKeys } from '@/services/queryKeys';

function buildSchema(minLength: number) {
  return z
    .object({
      current: z.string().min(1, 'common.required'),
      next: z.string().min(minLength, 'changePassword.minLength'),
      confirm: z.string().min(1, 'common.required'),
    })
    .refine((v) => v.next === v.confirm, { path: ['confirm'], message: 'changePassword.mismatch' });
}
type FormValues = z.infer<ReturnType<typeof buildSchema>>;

export function ChangePasswordForm({ minLength, onDone }: { minLength: number; onDone?: () => void }): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const schema = useMemo(() => buildSchema(minLength), [minLength]);
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState, reset } = useForm<FormValues>({ resolver: zodResolver(schema) });
  const message = (key?: string) => (key ? t(key, { min: minLength }) : undefined);

  // Not optimistic (HR20 exception): the result depends on the server checking the current password.
  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      await api.post('/api/auth/change-password', { current_password: values.current, new_password: values.next });
      reset();
      toast.success(t('changePassword.success'));
      await queryClient.invalidateQueries({ queryKey: queryKeys.me });
      onDone?.();
    } catch (error) {
      setServerError(errorMessage(t, error));
    }
  });

  return (
    <form className="flex max-w-[420px] flex-col gap-3" onSubmit={onSubmit} noValidate>
      <Field id="pw-current" label={t('changePassword.current')} error={message(formState.errors.current?.message)}>
        <Input type="password" autoComplete="current-password" {...register('current')} />
      </Field>
      <Field
        id="pw-new"
        label={t('changePassword.new')}
        hint={t('changePassword.minLength', { min: minLength })}
        error={message(formState.errors.next?.message)}
      >
        <Input type="password" autoComplete="new-password" {...register('next')} />
      </Field>
      <Field id="pw-confirm" label={t('changePassword.confirm')} error={message(formState.errors.confirm?.message)}>
        <Input type="password" autoComplete="new-password" {...register('confirm')} />
      </Field>
      {serverError ? (
        <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad">
          {serverError}
        </p>
      ) : null}
      <div>
        <Button type="submit" variant="primary" disabled={formState.isSubmitting}>
          {formState.isSubmitting ? t('common.saving') : t('changePassword.submit')}
        </Button>
      </div>
    </form>
  );
}
