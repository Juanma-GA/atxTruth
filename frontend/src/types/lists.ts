import type { TranslatableText } from './translatable';

export interface ValueListItem {
  id: string;
  list_id: string;
  code: string;
  label: TranslatableText;
  description: TranslatableText | null;
  sort_order: number;
  is_active: boolean;
  deleted_at: string | null;
}

export interface ValueList {
  id: string;
  code: string;
  name: TranslatableText;
  description: TranslatableText | null;
  is_system: boolean;
  item_count: number;
  active_item_count: number;
  updated_at: string;
  deleted_at: string | null;
}

export interface ValueListDetail extends ValueList {
  items: ValueListItem[];
}
