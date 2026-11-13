import { zodResolver } from '@hookform/resolvers/zod';
import { Copy } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Field } from '@/components/ui/field';
import { Input, Select } from '@/components/ui/input';
import { useCreateUser } from '@/hooks/useUsers';
import { errorMessage } from '@/services/apiErrors';
import { ROLES } from '@/lib/roles';
import type { User } from '@/types/api';

const createSchema = z.object({
  email: z.string().trim().email('errors.validation.failed'),
  display_name: z.string().trim().min(1, 'common.required').max(200),
  role: z.enum(['admin', 'editor', 'viewer']),
});
type CreateValues = z.infer<typeof createSchema>;

export function CreateUserDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (user: User, temporaryPassword: string) => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  const create = useCreateUser();
  const [serverError, setServerError] = useState<string | null>(null);
  const { register, handleSubmit, formState, reset } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { role: 'editor' },
  });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    try {
      const result = await create.mutateAsync(values);
      reset();
      onOpenChange(false);
      toast.success(t('users.created'));
      onCreated(result.user, result.temporary_password);
    } catch (error) {
      setServerError(errorMessage(t, error));
    }
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setServerError(null);
        onOpenChange(next);
      }}
    >
      <DialogContent
        title={t('users.createTitle')}
        footer={
          <>
            <Button onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button>
            <Button variant="primary" type="submit" form="create-user-form" disabled={formState.isSubmitting}>
              {formState.isSubmitting ? t('common.saving') : t('users.createSubmit')}
            </Button>
          </>
        }
      >
        <form id="create-user-form" className="grid gap-3 sm:grid-cols-2" onSubmit={onSubmit} noValidate>
          <Field id="nu-email" label={t('users.email')} error={formState.errors.email && t(formState.errors.email.message ?? '')}>
            <Input type="email" autoComplete="off" {...register('email')} />
          </Field>
          <Field
            id="nu-name"
            label={t('users.displayName')}
            error={formState.errors.display_name && t(formState.errors.display_name.message ?? '')}
          >
            <Input autoComplete="off" {...register('display_name')} />
          </Field>
          <Field id="nu-role" label={t('users.role')}>
            <Select {...register('role')}>
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(`roles.${role}`)}
                </option>
              ))}
            </Select>
          </Field>
          {serverError ? (
            <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad sm:col-span-2">
              {serverError}
            </p>
          ) : null}
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function TemporaryPasswordDialog({
  data,
  onClose,
}: {
  data: { email: string; password: string } | null;
  onClose: () => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  return (
    <Dialog open={data !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        title={t('users.tempTitle')}
        description={data ? t('users.tempIntro', { email: data.email }) : undefined}
        footer={
          <Button variant="primary" onClick={onClose}>
            {t('common.close')}
          </Button>
        }
      >
        <div className="flex items-center gap-2">
          <code data-testid="temporary-password" className="flex-1 rounded-small border border-line bg-sunk px-3 py-2 font-mono text-[15px] break-all">
            {data?.password}
          </code>
          <Button
            onClick={() => {
              if (data) void navigator.clipboard.writeText(data.password).then(() => toast.success(t('common.copied')));
            }}
          >
            <Copy aria-hidden="true" />
            {t('common.copy')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function DeleteUserDialog({
  user,
  onCancel,
  onConfirm,
}: {
  user: User | null;
  onCancel: () => void;
  onConfirm: (user: User, typedEmail: string) => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  const [typed, setTyped] = useState('');
  const matches = user !== null && typed.trim().toLowerCase() === user.email;
  return (
    <Dialog
      open={user !== null}
      onOpenChange={(open) => {
        if (!open) {
          setTyped('');
          onCancel();
        }
      }}
    >
      <DialogContent
        title={t('users.deleteTitle')}
        description={user ? t('users.deleteBody', { email: user.email }) : undefined}
        footer={
          <>
            <Button onClick={onCancel}>{t('common.cancel')}</Button>
            <Button
              variant="danger"
              disabled={!matches}
              onClick={() => {
                if (user) onConfirm(user, typed.trim());
                setTyped('');
              }}
            >
              {t('users.deletePermanently')}
            </Button>
          </>
        }
      >
        <Field id="del-email" label={t('users.typeEmail')}>
          <Input value={typed} autoComplete="off" onChange={(e) => setTyped(e.target.value)} />
        </Field>
      </DialogContent>
    </Dialog>
  );
}
