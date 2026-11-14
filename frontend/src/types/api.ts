import type { Language } from '@/i18n';
import type { ThemePreference } from '@/lib/theme';

import type { TranslatableText } from './translatable';

export type Role = 'admin' | 'editor' | 'viewer';

export interface PublicConfig {
  app_name: string;
  default_language: Language;
  auth_mode: 'local' | 'oidc';
  languages: Language[];
  password_min_length: number;
}

export interface ClientConfig extends PublicConfig {
  table_page_size: number;
  max_image_mb: number;
}

export interface Me {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  preferred_language: Language | null;
  theme: ThemePreference;
  must_change_password: boolean;
  last_login_at: string | null;
}

export type SettingType = 'string' | 'integer' | 'number' | 'boolean' | 'enum' | 'object';

export interface SettingProperty {
  type: SettingType;
  min?: number;
  max?: number;
  unit?: string;
  label?: TranslatableText;
  options?: string[];
}

export interface SettingConstraints {
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  options?: string[];
  unit?: string;
  properties?: Record<string, SettingProperty>;
}

export type SettingValue = string | number | boolean | Record<string, unknown>;

export interface Setting {
  key: string;
  category: string;
  sort_order: number;
  value_type: SettingType;
  value: SettingValue;
  default_value: SettingValue;
  constraints: SettingConstraints;
  label: TranslatableText;
  description: TranslatableText;
  updated_at: string;
}

export interface InfrastructureItem {
  key: string;
  value: string;
  secret: boolean;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  preferred_language: Language | null;
  must_change_password: boolean;
  created_at: string;
  last_login_at: string | null;
  deleted_at: string | null;
}

export interface UserWithTemporaryPassword {
  user: User;
  temporary_password: string;
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_email: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  target_label: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  source: string;
  source_detail: string | null;
}

export interface AuditPage {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}
