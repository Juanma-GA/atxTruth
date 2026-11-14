export type ExcelDomain = 'lists' | 'taxonomy';
export type RowAction = 'create' | 'update' | 'delete' | 'unchanged' | 'error';

export interface Issue {
  code: string;
  column: string | null;
  params: Record<string, unknown>;
}

export interface RowChange {
  field: string;
  column: string;
  before: unknown;
  after: unknown;
}

export interface ReportRow {
  row: number | null;
  key: string;
  action: RowAction;
  changes: RowChange[];
  errors: Issue[];
  warnings: Issue[];
}

export interface ReportSheet {
  sheet: string;
  present: boolean;
  counts: Record<'create' | 'update' | 'delete' | 'unchanged' | 'error_rows' | 'not_in_file', number>;
  not_in_file: string[];
  rows: ReportRow[];
}

export interface ImportReport {
  domain: string;
  file_name: string | null;
  applied: boolean;
  ok: boolean;
  summary: Record<
    'create' | 'update' | 'delete' | 'unchanged' | 'error_rows' | 'errors' | 'warnings' | 'not_in_file' | 'special_values',
    number
  >;
  errors: Issue[];
  warnings: Issue[];
  special_values: Record<string, Record<string, number>>;
  sheets: ReportSheet[];
}
