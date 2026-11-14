import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { TranslatableTextEditor } from '@/components/translatable/TranslatableTextEditor';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Field } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import type { ValueList, ValueListItem } from '@/types/lists';
import { normalizeTranslatable, translationOf, type TranslatableText } from '@/types/translatable';

const CODE_RE = /^[a-z0-9]+(?:_[a-z0-9]+)*$/;
const EMPTY: TranslatableText = { en: '' };

function optional(text: TranslatableText): TranslatableText | null {
  return translationOf(text, 'en') === null ? null : normalizeTranslatable(text);
}

interface ListFormValue {
  code: string;
  name: TranslatableText;
  description: TranslatableText | null;
}

export function ListDialog({
  open,
  initial,
  onCancel,
  onSubmit,
  busy,
  error,
}: {
  open: boolean;
  initial: ValueList | null;
  onCancel: () => void;
  onSubmit: (value: ListFormValue) => void;
  busy?: boolean;
  error?: string | null;
}): React.JSX.Element {
  const { t } = useTranslation();
  const [code, setCode] = useState('');
  const [name, setName] = useState<TranslatableText>(EMPTY);
  const [description, setDescription] = useState<TranslatableText>(EMPTY);
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (open) {
      setCode(initial?.code ?? '');
      setName(initial?.name ?? EMPTY);
      setDescription(initial?.description ?? EMPTY);
      setTouched(false);
    }
  }, [open, initial]);
  const codeError = touched && !CODE_RE.test(code) ? t('errors.value_lists.invalid_code', { code }) : undefined;
  const nameError = touched && !translationOf(name, 'en') ? t('translatable.required') : undefined;
  const codeChanged = initial !== null && code !== initial.code;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent
        title={initial ? t('lists.editList') : t('lists.newList')}
        footer={
          <>
            <Button onClick={onCancel}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={busy}
              onClick={() => {
                setTouched(true);
                if (!CODE_RE.test(code) || !translationOf(name, 'en')) return;
                onSubmit({ code, name: normalizeTranslatable(name), description: optional(description) });
              }}
            >
              {initial ? t('common.save') : t('common.create')}
            </Button>
          </>
        }
      >
        <Field
          id="list-code"
          label={t('lists.code')}
          hint={initial?.is_system ? t('lists.systemHint') : codeChanged ? t('lists.codeChangeWarning') : t('lists.codeHint')}
          error={codeError}
        >
          <Input
            value={code}
            className="font-mono"
            disabled={initial?.is_system}
            maxLength={64}
            onChange={(e) => setCode(e.target.value.trim())}
          />
        </Field>
        <TranslatableTextEditor label={t('lists.name')} value={name} onChange={setName} maxLength={200} error={nameError} />
        <TranslatableTextEditor
          label={t('lists.description_label')}
          value={description}
          onChange={setDescription}
          multiline
          maxLength={2000}
        />
        {error ? (
          <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad">
            {error}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export interface ItemFormValue {
  code?: string;
  label: TranslatableText;
  description: TranslatableText | null;
  is_active: boolean;
}

export function ItemDialog({
  open,
  initial,
  onCancel,
  onSubmit,
  busy,
  error,
}: {
  open: boolean;
  initial: ValueListItem | null;
  onCancel: () => void;
  onSubmit: (value: ItemFormValue) => void;
  busy?: boolean;
  error?: string | null;
}): React.JSX.Element {
  const { t } = useTranslation();
  const [code, setCode] = useState('');
  const [label, setLabel] = useState<TranslatableText>(EMPTY);
  const [description, setDescription] = useState<TranslatableText>(EMPTY);
  const [active, setActive] = useState(true);
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (open) {
      setCode(initial?.code ?? '');
      setLabel(initial?.label ?? EMPTY);
      setDescription(initial?.description ?? EMPTY);
      setActive(initial?.is_active ?? true);
      setTouched(false);
    }
  }, [open, initial]);
  const codeInvalid = code !== '' && !CODE_RE.test(code);
  const codeError = touched && (codeInvalid || (initial !== null && code === '')) ? t('errors.value_lists.invalid_item_code', { code }) : undefined;
  const labelError = touched && !translationOf(label, 'en') ? t('translatable.required') : undefined;
  const codeChanged = initial !== null && code !== initial.code;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent
        title={initial ? t('lists.editItem') : t('lists.newItem')}
        footer={
          <>
            <Button onClick={onCancel}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={busy}
              onClick={() => {
                setTouched(true);
                if (codeInvalid || (initial !== null && code === '') || !translationOf(label, 'en')) return;
                onSubmit({
                  ...(code ? { code } : {}),
                  label: normalizeTranslatable(label),
                  description: optional(description),
                  is_active: active,
                });
              }}
            >
              {initial ? t('common.save') : t('common.create')}
            </Button>
          </>
        }
      >
        <Field
          id="item-code"
          label={t('lists.code')}
          hint={codeChanged ? t('lists.codeChangeWarning') : initial ? t('lists.codeHint') : `${t('lists.codeHint')} ${t('lists.itemCodeHint')}`}
          error={codeError}
        >
          <Input value={code} className="font-mono" maxLength={64} onChange={(e) => setCode(e.target.value.trim())} />
        </Field>
        <TranslatableTextEditor label={t('lists.label')} value={label} onChange={setLabel} maxLength={200} error={labelError} />
        <TranslatableTextEditor
          label={t('lists.description_label')}
          value={description}
          onChange={setDescription}
          multiline
          maxLength={2000}
        />
        <label className="flex items-center gap-2 text-[13px]">
          <Switch checked={active} onCheckedChange={setActive} aria-label={t('lists.active')} />
          {active ? t('lists.active') : t('lists.inactive')}
        </label>
        {error ? (
          <p role="alert" className="m-0 rounded-base bg-bad-soft px-3 py-2 text-[13px] font-medium text-bad">
            {error}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
