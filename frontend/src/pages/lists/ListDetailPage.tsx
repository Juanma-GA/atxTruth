import { ArrowDown, ArrowUp, ChevronLeft, GripVertical, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

import { PageHeader } from '@/components/layout/PageHeader';
import { ItemDialog, ListDialog } from '@/components/lists/ListDialogs';
import { TranslatedText } from '@/components/translatable/TranslatedText';
import { TranslationCell } from '@/components/translatable/TranslationCell';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { Switch } from '@/components/ui/switch';
import { Table, TableWrap, Td, Th } from '@/components/ui/table';
import {
  useCreateItem,
  useDeleteItem,
  useDeleteList,
  useReorderItems,
  useRestoreItem,
  useUpdateItem,
  useUpdateList,
  useValueList,
} from '@/hooks/useValueLists';
import { LANGUAGES } from '@/i18n';
import { errorMessage } from '@/services/apiErrors';
import type { Me } from '@/types/api';
import type { ValueListItem } from '@/types/lists';

function move<T>(list: T[], from: number, to: number): T[] {
  const copy = [...list];
  const [item] = copy.splice(from, 1);
  if (item !== undefined) copy.splice(to, 0, item);
  return copy;
}

export function ListDetailPage({ me }: { me: Me }): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { listId = '' } = useParams();
  const isAdmin = me.role === 'admin';
  const [showDeleted, setShowDeleted] = useState(false);
  const detail = useValueList(listId, showDeleted);
  const createItem = useCreateItem(listId);
  const updateItem = useUpdateItem(listId);
  const deleteItem = useDeleteItem(listId, showDeleted);
  const restoreItem = useRestoreItem(listId);
  const reorder = useReorderItems(listId);
  const updateList = useUpdateList(listId);
  const deleteList = useDeleteList(false);
  const [editing, setEditing] = useState<ValueListItem | 'new' | null>(null);
  const [itemError, setItemError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<ValueListItem | null>(null);
  const [editingList, setEditingList] = useState(false);
  const [deletingList, setDeletingList] = useState(false);
  const [dragged, setDragged] = useState<string | null>(null);

  if (detail.isPending) return <p className="text-muted">{t('common.loading')}</p>;
  if (detail.isError) {
    return (
      <div className="flex flex-col gap-3">
        <p role="alert" className="text-bad">{errorMessage(t, detail.error)}</p>
        <Link to="/lists" className="text-accent">
          {t('lists.allLists')}
        </Link>
      </div>
    );
  }
  const list = detail.data;
  const live = list.items.filter((i) => !i.deleted_at);
  const rows = list.items;

  const reorderTo = (from: number, to: number) => {
    if (to < 0 || to >= live.length || from === to) return;
    reorder.mutate({ ids: move(live, from, to).map((i) => i.id) });
  };

  return (
    <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-4">
      <Link to="/lists" className="inline-flex items-center gap-1 text-[13px] text-muted hover:text-ink">
        <ChevronLeft className="size-4" aria-hidden="true" />
        {t('lists.allLists')}
      </Link>
      <PageHeader
        title={<TranslatedText text={list.name} />}
        actions={
          isAdmin ? (
            <>
              <Button onClick={() => setEditingList(true)}>
                <Pencil aria-hidden="true" />
                {t('lists.editList')}
              </Button>
              {!list.is_system ? (
                <Button variant="dangerOutline" onClick={() => setDeletingList(true)}>
                  <Trash2 aria-hidden="true" />
                  {t('lists.deleteList')}
                </Button>
              ) : null}
              <Button variant="primary" onClick={() => setEditing('new')}>
                <Plus aria-hidden="true" />
                {t('lists.newItem')}
              </Button>
            </>
          ) : null
        }
      />
      <div className="-mt-2 flex flex-wrap items-center gap-2 text-[13px]">
        <span className="font-mono text-muted">{list.code}</span>
        {list.is_system ? (
          <Badge tone="info" title={t('lists.systemHint')}>
            {t('lists.system')}
          </Badge>
        ) : null}
      </div>
      {list.description ? (
        <p className="m-0 max-w-[70ch] text-muted">
          <TranslatedText text={list.description} />
        </p>
      ) : null}
      {list.is_system ? <p className="m-0 text-[13px] text-muted">{t('lists.systemHint')}</p> : null}
      {!isAdmin ? <p className="m-0 text-[13px] text-muted">{t('lists.readOnly')}</p> : null}
      {isAdmin ? (
        <label className="flex items-center gap-2 text-[13px]">
          <Switch checked={showDeleted} onCheckedChange={setShowDeleted} aria-label={t('lists.showDeleted')} />
          {t('lists.showDeleted')}
        </label>
      ) : null}
      <Card>
        <TableWrap>
          <Table>
            <thead>
              <tr>
                <Th scope="col">{t('lists.order')}</Th>
                <Th scope="col">{t('lists.code')}</Th>
                {LANGUAGES.map((lang) => (
                  <Th key={lang} scope="col">
                    {t('lists.label')} [{t(`languages.short.${lang}`)}]
                  </Th>
                ))}
                <Th scope="col">{t('lists.active')}</Th>
                {isAdmin ? <Th scope="col">{t('common.actions')}</Th> : null}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <Td colSpan={7} className="text-muted">
                    {t('lists.emptyItems')}
                  </Td>
                </tr>
              ) : (
                rows.map((item) => {
                  const index = live.findIndex((i) => i.id === item.id);
                  const label = item.code;
                  return (
                    <tr
                      key={item.id}
                      data-item={item.code}
                      className={item.deleted_at ? 'opacity-60' : dragged === item.id ? 'bg-accent-soft' : undefined}
                      draggable={isAdmin && !item.deleted_at}
                      onDragStart={() => setDragged(item.id)}
                      onDragEnd={() => setDragged(null)}
                      onDragOver={(e) => {
                        if (dragged && !item.deleted_at) e.preventDefault();
                      }}
                      onDrop={(e) => {
                        e.preventDefault();
                        const from = live.findIndex((i) => i.id === dragged);
                        setDragged(null);
                        if (from >= 0 && index >= 0) reorderTo(from, index);
                      }}
                    >
                      <Td className="whitespace-nowrap">
                        {isAdmin && !item.deleted_at ? (
                          <span className="flex items-center gap-0.5">
                            <GripVertical className="size-4 cursor-grab text-muted" aria-label={t('lists.dragHandle', { label })} />
                            <Button
                              size="icon"
                              variant="ghost"
                              className="size-7"
                              aria-label={t('lists.moveUp', { label })}
                              disabled={index <= 0}
                              onClick={() => reorderTo(index, index - 1)}
                            >
                              <ArrowUp aria-hidden="true" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="size-7"
                              aria-label={t('lists.moveDown', { label })}
                              disabled={index >= live.length - 1}
                              onClick={() => reorderTo(index, index + 1)}
                            >
                              <ArrowDown aria-hidden="true" />
                            </Button>
                          </span>
                        ) : (
                          <span className="tabular-nums text-muted">{index >= 0 ? index + 1 : t('common.none')}</span>
                        )}
                      </Td>
                      <Td className="font-mono text-[12.5px]">{item.code}</Td>
                      {LANGUAGES.map((lang) => (
                        <Td key={lang}>
                          <TranslationCell text={item.label} language={lang} />
                        </Td>
                      ))}
                      <Td>
                        {item.deleted_at ? (
                          <Badge tone="bad">{t('lists.deleted')}</Badge>
                        ) : isAdmin ? (
                          <Switch
                            checked={item.is_active}
                            aria-label={`${t('lists.active')}: ${label}`}
                            onCheckedChange={(checked) => updateItem.mutate({ id: item.id, changes: { is_active: checked } })}
                          />
                        ) : (
                          <Badge tone={item.is_active ? 'ok' : 'plain'}>{item.is_active ? t('lists.active') : t('lists.inactive')}</Badge>
                        )}
                      </Td>
                      {isAdmin ? (
                        <Td className="whitespace-nowrap">
                          {item.deleted_at ? (
                            <Button size="sm" onClick={() => restoreItem.mutate({ id: item.id })}>
                              <RotateCcw aria-hidden="true" />
                              {t('common.restore')}
                            </Button>
                          ) : (
                            <span className="flex gap-1">
                              <Button size="sm" onClick={() => setEditing(item)} aria-label={`${t('common.edit')}: ${label}`}>
                                <Pencil aria-hidden="true" />
                                {t('common.edit')}
                              </Button>
                              <Button
                                size="sm"
                                variant="dangerOutline"
                                onClick={() => setToDelete(item)}
                                aria-label={`${t('common.delete')}: ${label}`}
                              >
                                <Trash2 aria-hidden="true" />
                              </Button>
                            </span>
                          )}
                        </Td>
                      ) : null}
                    </tr>
                  );
                })
              )}
            </tbody>
          </Table>
        </TableWrap>
      </Card>

      <ItemDialog
        open={editing !== null}
        initial={editing === 'new' ? null : editing}
        busy={createItem.isPending}
        error={itemError}
        onCancel={() => {
          setEditing(null);
          setItemError(null);
        }}
        onSubmit={(value) => {
          setItemError(null);
          if (editing === 'new') {
            createItem.mutate(value, {
              onSuccess: () => {
                setEditing(null);
                toast.success(t('lists.itemCreated'));
              },
              onError: (err) => setItemError(errorMessage(t, err)),
            });
          } else if (editing) {
            updateItem.mutate({ id: editing.id, changes: value });
            setEditing(null);
          }
        }}
      />
      <ListDialog
        open={editingList}
        initial={list}
        onCancel={() => setEditingList(false)}
        onSubmit={(value) => {
          updateList.mutate(list.is_system ? { name: value.name, description: value.description } : value);
          setEditingList(false);
        }}
      />
      <ConfirmDialog
        open={toDelete !== null}
        title={t('lists.confirmDeleteItemTitle')}
        body={t('lists.confirmDeleteItemBody', { label: toDelete?.code ?? '' })}
        confirmLabel={t('common.delete')}
        onCancel={() => setToDelete(null)}
        onConfirm={() => {
          if (toDelete) deleteItem.mutate({ id: toDelete.id });
          setToDelete(null);
        }}
      />
      <ConfirmDialog
        open={deletingList}
        title={t('lists.confirmDeleteListTitle')}
        body={t('lists.confirmDeleteListBody', { name: list.code })}
        confirmLabel={t('lists.deleteList')}
        onCancel={() => setDeletingList(false)}
        onConfirm={() => {
          setDeletingList(false);
          deleteList.mutate(list.id, { onSuccess: () => navigate('/lists') });
        }}
      />
    </div>
  );
}
