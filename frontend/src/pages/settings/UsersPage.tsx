import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { KeyRound, Plus, RotateCcw, Trash2, UserX } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { PageHeader } from '@/components/layout/PageHeader';
import { CreateUserDialog, DeleteUserDialog, TemporaryPasswordDialog } from '@/components/settings/UserDialogs';
import { ROLES } from '@/lib/roles';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/input';
import { Pagination } from '@/components/ui/pagination';
import { Switch } from '@/components/ui/switch';
import { Table, TableWrap, Td, Th } from '@/components/ui/table';
import { useClientConfig } from '@/hooks/useConfig';
import {
  useChangeRole,
  useDeactivateUser,
  useDeleteUserPermanently,
  useResetPassword,
  useRestoreUser,
  useUsers,
} from '@/hooks/useUsers';
import { errorMessage } from '@/services/apiErrors';
import type { Me, Role, User } from '@/types/api';

const column = createColumnHelper<User>();

export function UsersPage({ me }: { me: Me }): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const [showDeleted, setShowDeleted] = useState(false);
  const [pageIndex, setPageIndex] = useState(0);
  const [creating, setCreating] = useState(false);
  const [temporary, setTemporary] = useState<{ email: string; password: string } | null>(null);
  const [toDelete, setToDelete] = useState<User | null>(null);
  const users = useUsers(showDeleted);
  const config = useClientConfig();
  const changeRole = useChangeRole();
  const deactivate = useDeactivateUser(showDeleted);
  const restore = useRestoreUser();
  const deletePermanently = useDeleteUserPermanently();
  const resetPassword = useResetPassword();
  const pageSize = config.data?.table_page_size ?? 25;

  const dateFormat = useMemo(
    () => new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' }),
    [i18n.language],
  );

  const columns = useMemo(
    () => [
      column.accessor('display_name', {
        header: () => t('users.displayName'),
        cell: (info) => (
          <span>
            {info.getValue()}
            {info.row.original.id === me.id ? <span className="text-muted"> ({t('users.you')})</span> : null}
          </span>
        ),
      }),
      column.accessor('email', {
        header: () => t('users.email'),
        cell: (info) => <span className="font-mono text-[12.5px]">{info.getValue()}</span>,
      }),
      column.accessor('role', {
        header: () => t('users.role'),
        cell: (info) => {
          const user = info.row.original;
          const disabled = user.id === me.id || user.deleted_at !== null;
          return (
            <Select
              aria-label={`${t('users.role')}: ${user.email}`}
              className="min-w-36"
              value={user.role}
              disabled={disabled}
              onChange={(e) => changeRole.mutate({ id: user.id, role: e.target.value as Role })}
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(`roles.${role}`)}
                </option>
              ))}
            </Select>
          );
        },
      }),
      column.display({
        id: 'status',
        header: () => t('users.status'),
        cell: ({ row }) => {
          const user = row.original;
          if (user.deleted_at) return <Badge tone="bad">{t('users.deactivated')}</Badge>;
          return (
            <span className="flex flex-wrap gap-1">
              <Badge tone="ok">{t('users.active')}</Badge>
              {user.must_change_password ? <Badge tone="warn">{t('users.pendingPassword')}</Badge> : null}
            </span>
          );
        },
      }),
      column.accessor('last_login_at', {
        header: () => t('users.lastLogin'),
        cell: (info) => {
          const value = info.getValue();
          return value ? dateFormat.format(new Date(value)) : <span className="text-muted">{t('users.never')}</span>;
        },
      }),
      column.display({
        id: 'actions',
        header: () => t('common.actions'),
        cell: ({ row }) => {
          const user = row.original;
          if (user.id === me.id) return null;
          if (user.deleted_at) {
            return (
              <span className="flex flex-wrap gap-1">
                <Button size="sm" onClick={() => restore.mutate({ id: user.id })}>
                  <RotateCcw aria-hidden="true" />
                  {t('users.restore')}
                </Button>
                <Button size="sm" variant="dangerOutline" onClick={() => setToDelete(user)}>
                  <Trash2 aria-hidden="true" />
                  {t('users.deletePermanently')}
                </Button>
              </span>
            );
          }
          return (
            <span className="flex flex-wrap gap-1">
              <Button
                size="sm"
                onClick={() =>
                  resetPassword.mutate(user.id, {
                    onSuccess: (r) => setTemporary({ email: r.user.email, password: r.temporary_password }),
                  })
                }
              >
                <KeyRound aria-hidden="true" />
                {t('users.resetPassword')}
              </Button>
              <Button size="sm" variant="dangerOutline" onClick={() => deactivate.mutate({ id: user.id })}>
                <UserX aria-hidden="true" />
                {t('users.deactivate')}
              </Button>
            </span>
          );
        },
      }),
    ],
    [t, me.id, dateFormat, changeRole, restore, resetPassword, deactivate],
  );

  const table = useReactTable({
    data: users.data ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getRowId: (row) => row.id,
    state: { pagination: { pageIndex, pageSize } },
    autoResetPageIndex: false,
  });

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t('users.title')}
        description={t('users.description')}
        actions={
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus aria-hidden="true" />
            {t('users.create')}
          </Button>
        }
      />
      <label className="flex items-center gap-2 text-[13px]">
        <Switch checked={showDeleted} onCheckedChange={setShowDeleted} aria-label={t('users.showDeactivated')} />
        {t('users.showDeactivated')}
      </label>
      {users.isError ? <p role="alert" className="text-bad">{errorMessage(t, users.error)}</p> : null}
      <Card>
        <TableWrap>
          <Table>
            <thead>
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <Th key={header.id} scope="col">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </Th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {users.isPending ? (
                <tr>
                  <Td colSpan={columns.length} className="text-muted">
                    {t('common.loading')}
                  </Td>
                </tr>
              ) : table.getRowModel().rows.length === 0 ? (
                <tr>
                  <Td colSpan={columns.length} className="text-muted">
                    {t('users.empty')}
                  </Td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr key={row.id} data-user={row.original.email}>
                    {row.getVisibleCells().map((cell) => (
                      <Td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</Td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </TableWrap>
        <Pagination
          page={pageIndex + 1}
          pages={table.getPageCount()}
          total={users.data?.length ?? 0}
          onPage={(page) => setPageIndex(page - 1)}
        />
      </Card>
      <CreateUserDialog
        open={creating}
        onOpenChange={setCreating}
        onCreated={(user, password) => setTemporary({ email: user.email, password })}
      />
      <TemporaryPasswordDialog data={temporary} onClose={() => setTemporary(null)} />
      <DeleteUserDialog
        user={toDelete}
        onCancel={() => setToDelete(null)}
        onConfirm={(user, email) => {
          setToDelete(null);
          deletePermanently.mutate({ id: user.id, confirm_email: email });
        }}
      />
    </div>
  );
}
