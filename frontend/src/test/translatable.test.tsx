import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import { TranslatableTextEditor } from '@/components/translatable/TranslatableTextEditor';
import { TranslatedText } from '@/components/translatable/TranslatedText';
import i18n from '@/i18n';
import { missingLanguages, normalizeTranslatable, translationOf, type TranslatableText } from '@/types/translatable';

afterEach(async () => {
  await i18n.changeLanguage('en');
});

describe('TranslatableText helpers', () => {
  it('treats blank translations as missing', () => {
    const text: TranslatableText = { en: 'Hello', es: '  ', fr: null };
    expect(translationOf(text, 'es')).toBeNull();
    expect(missingLanguages(text)).toEqual(['es', 'fr']);
    expect(normalizeTranslatable({ en: ' Hello ', es: ' Hola ', fr: '' })).toEqual({ en: 'Hello', es: 'Hola' });
  });
});

describe('TranslatedText', () => {
  it('shows the translation in the interface language', async () => {
    await i18n.changeLanguage('es');
    render(<TranslatedText text={{ en: 'Hello', es: 'Hola' }} />);
    expect(screen.getByText('Hola')).toBeInTheDocument();
  });

  it('says when the translation is missing instead of silently showing English (HR7)', async () => {
    await i18n.changeLanguage('fr');
    render(<TranslatedText text={{ en: 'Hello' }} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Pas de traduction FR')).toBeInTheDocument();
  });
});

function Harness({ initial }: { initial: TranslatableText }) {
  const [value, setValue] = useState(initial);
  return (
    <>
      <TranslatableTextEditor label="Title" value={value} onChange={setValue} />
      <output data-testid="value">{JSON.stringify(value)}</output>
    </>
  );
}

describe('TranslatableTextEditor', () => {
  it('has one tab per language and marks the missing ones', () => {
    render(<Harness initial={{ en: 'Hello', es: 'Hola' }} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs.map((t) => t.textContent)).toEqual(['EN', 'ES', 'FR']);
    expect(screen.getAllByRole('img', { name: 'No FR translation' })).toHaveLength(1);
    expect(screen.queryByRole('img', { name: 'No ES translation' })).toBeNull();
  });

  it('edits each language and clears the marker once translated', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ en: 'Hello' }} />);
    await user.click(screen.getByRole('tab', { name: /FR/ }));
    const fr = screen.getByLabelText('Title (French)');
    await user.type(fr, 'Bonjour');
    expect(JSON.parse(screen.getByTestId('value').textContent ?? '{}')).toEqual({ en: 'Hello', fr: 'Bonjour' });
    expect(screen.queryByRole('img', { name: 'No FR translation' })).toBeNull();
    expect(screen.getByRole('img', { name: 'No ES translation' })).toBeInTheDocument();
  });

  it('flags the master language as required', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ en: 'Hello' }} />);
    await user.clear(screen.getByLabelText('Title (English)'));
    expect(screen.getByRole('img', { name: 'No EN translation' })).toBeInTheDocument();
    expect(screen.getByLabelText('Title (English)')).toBeRequired();
  });
});
