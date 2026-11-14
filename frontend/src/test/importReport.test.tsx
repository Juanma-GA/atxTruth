import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { ImportReportView } from '@/components/excel/ImportReportView';
import i18n from '@/i18n';
import type { ImportReport } from '@/types/excel';

const report: ImportReport = {
  domain: 'taxonomy',
  file_name: 'taxonomy.xlsx',
  applied: false,
  ok: false,
  summary: { create: 1, update: 1, delete: 0, unchanged: 3, error_rows: 1, errors: 1, warnings: 1, not_in_file: 2, special_values: 1 },
  errors: [],
  warnings: [],
  special_values: { to_complete: { Owner: 1 } },
  sheets: [
    {
      sheet: 'Services',
      present: true,
      counts: { create: 1, update: 1, delete: 0, unchanged: 3, error_rows: 1, not_in_file: 2 },
      not_in_file: ['S9.1', 'S9.2'],
      rows: [
        { row: 2, key: 'S1.1.1', action: 'update', changes: [{ field: 'name.en', column: 'Name [EN]', before: 'Old', after: 'New' }], errors: [], warnings: [] },
        { row: 3, key: 'S1.1.2', action: 'unchanged', changes: [], errors: [], warnings: [{ code: 'excel.translation_missing', column: 'Name', params: { languages: ['es', 'fr'] } }] },
        { row: 4, key: 'S1.1.3', action: 'update', changes: [], errors: [{ code: 'excel.unknown_reference', column: 'Family', params: { value: 'F9.9', sheet: 'Families' } }], warnings: [] },
        { row: 5, key: 'S1.1.9', action: 'create', changes: [{ field: 'name.en', column: 'Name [EN]', before: null, after: 'Brand new' }], errors: [], warnings: [] },
      ],
    },
  ],
};

afterEach(async () => {
  await i18n.changeLanguage('en');
});

describe('ImportReportView', () => {
  it('opens on the errors when the file has errors, with row, column and a translated reason', () => {
    render(<ImportReportView report={report} />);
    const rows = screen.getAllByRole('row').slice(1);
    expect(rows).toHaveLength(1);
    const cells = within(rows[0] as HTMLElement).getAllByRole('cell');
    expect(cells.map((c) => c.textContent)).toEqual(['Services', '4', 'S1.1.3', 'Error', 'Family: F9.9 does not exist in Families.']);
  });

  it('filters by kind of change and humanises values and parameters', async () => {
    const user = userEvent.setup();
    await i18n.changeLanguage('es');
    render(<ImportReportView report={report} />);
    await user.selectOptions(screen.getByLabelText('Mostrar'), 'all');
    expect(screen.getByText('Old → New')).toBeInTheDocument();
    expect(screen.getByText('(vacío) → Brand new')).toBeInTheDocument();
    expect(screen.getByText('Sin traducción: ES, FR.')).toBeInTheDocument();
    expect(screen.getByText('Por completar en Owner: 1')).toBeInTheDocument();
    expect(screen.getByText(/2 filas están en la aplicación pero no en el fichero/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Mostrar'), 'create');
    expect(screen.getAllByRole('row').slice(1).map((r) => r.getAttribute('data-report-row'))).toEqual(['Services:S1.1.9']);
  });
});
