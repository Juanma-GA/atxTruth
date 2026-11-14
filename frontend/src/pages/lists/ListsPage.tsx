import { Plus, RotateCcw } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { ExcelActions } from '@/components/excel/ExcelActions';
import { PageHeader } from '@/components/layout/PageHeader';
import { ListDialog } from '@/components/lists/ListDialogs';
import { TranslatedText } from '@/components/translatable/TranslatedText';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Table, TableWrap, Td, Th } from '@/components/ui/table';
import { useCreateList, useRestoreList, useValueLists } from '@/hooks/useValueLists';
import { errorMessage } from '@/services/apiErrors';
import { queryKeys } from '@/services/queryKeys';
import type { Me } from '@/types/api';

export function ListsPage({ me }: { me: Me }): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isAdmin = me.role === 'admin';
  const [showDeleted, setShowDeleted] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const lists = useValueLists(showDeleted);
  const create = useCreateList();
  const restore = useRestoreList();

  return (
    <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-4">
      <PageHeader
        title={t('lists.title')}
        description={t('lists.description')}
        actions={
          <>
            <ExcelActions domain="lists" canImport={isAdmin} invalidate={[queryKeys.valueListsAll, ['valueList']]} />
            {isAdmin ? (
              <Button variant="primary" onClick={() => setCreating(true)}>
                <Plus aria-hidden="true" />
                {t('lists.newList')}
              </Button>
            ) : null}
          </>
        }
      />
      {!isAdmin ? <p className="m-0 text-[13px] text-muted">{t('lists.readOnly')}</p> : null}
      {isAdmin ? (
        <label className="flex items-center gap-2 text-[13px]">
          <Switch checked={showDeleted} onCheckedChange={setShowDeleted} aria-label={t('lists.showDeleted')} />
          {t('lists.showDeleted')}
        </label>
      ) : null}
      {lists.isError ? <p role="alert" className="text-bad">{errorMessage(t, lists.error)}</p> : null}
      <Card>
        <TableWrap>
          <Table>
            <thead>
              <tr>
                <Th scope="col">{t('lists.name')}</Th>
                <Th scope="col">{t('lists.code')}</Th>
                <Th scope="col">{t('lists.activeItems')}</Th>
                <Th scope="col">{t('lists.system')}</Th>
                {isAdmin && showDeleted ? <Th scope="col">{t('common.actions')}</Th> : null}
              </tr>
            </thead>
            <tbody>
              {lists.isPending ? (
                <tr>
                  <Td colSpan={5} className="text-muted">
                    {t('common.loading')}
                  </Td>
                </tr>
              ) : (lists.data ?? []).length === 0 ? (
                <tr>
                  <Td colSpan={5} className="text-muted">
                    {t('lists.emptyLists')}
                  </Td>
                </tr>
              ) : (
                (lists.data ?? []).map((list) => (
                  <tr key={list.id} data-list={list.code} className={list.deleted_at ? 'opacity-60' : undefined}>
                    <Td>
                      {list.deleted_at ? (
                        <TranslatedText text={list.name} />
                      ) : (
                        <Link to={`/lists/${list.id}`} className="font-medium text-accent hover:underline">
                          <TranslatedText text={list.name} />
                        </Link>
                      )}
                      {list.deleted_at ? (
                        <Badge tone="bad" className="ml-2">
                          {t('lists.deleted')}
                        </Badge>
                      ) : null}
                    </Td>
                    <Td className="font-mono text-[12.5px]">{list.code}</Td>
                    <Td className="tabular-nums">
                      {list.active_item_count} / {list.item_count}
                    </Td>
                    <Td>{list.is_system ? <Badge tone="info">{t('lists.system')}</Badge> : null}</Td>
                    {isAdmin && showDeleted ? (
                      <Td>
                        {list.deleted_at ? (
                          <Button size="sm" onClick={() => restore.mutate(list.id)}>
                            <RotateCcw aria-hidden="true" />
                            {t('common.restore')}
                          </Button>
                        ) : null}
                      </Td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </TableWrap>
      </Card>
      <ListDialog
        open={creating}
        initial={null}
        busy={create.isPending}
        error={createError}
        onCancel={() => {
          setCreating(false);
          setCreateError(null);
        }}
        onSubmit={(value) => {
          setCreateError(null);
          create.mutate(value, {
            onSuccess: (created) => {
              setCreating(false);
              toast.success(t('lists.listCreated'));
              navigate(`/lists/${created.id}`);
            },
            onError: (err) => setCreateError(errorMessage(t, err)),
          });
        }}
      />
    </div>
  );
}
