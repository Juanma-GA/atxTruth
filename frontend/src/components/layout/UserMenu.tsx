import { ChevronDown, KeyRound, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useSignOut } from '@/hooks/useSession';
import type { Me } from '@/types/api';

export function UserMenu({ me, canChangePassword }: { me: Me; canChangePassword: boolean }): React.JSX.Element {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const signOut = useSignOut();
  const initials = me.display_name
    .split(/\s+/)
    .map((part) => part.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" aria-label={t('shell.userMenu')} className="px-1.5">
          <span
            aria-hidden="true"
            className="inline-grid size-7 place-items-center rounded-full bg-accent text-[11.5px] font-semibold text-accent-ink"
          >
            {initials}
          </span>
          <span className="max-w-40 truncate max-[860px]:hidden">{me.display_name}</span>
          <ChevronDown aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="px-2.5 py-1.5">
          <span className="block text-xs text-muted">{t('shell.signedInAs')}</span>
          <span className="block font-semibold">{me.display_name}</span>
          <span className="block text-xs text-muted">
            {me.email} · {t(`roles.${me.role}`)}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {canChangePassword ? (
          <DropdownMenuItem onSelect={() => navigate('/settings/account#password')}>
            <KeyRound aria-hidden="true" />
            {t('shell.changePassword')}
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem
          onSelect={() => {
            void signOut().then(() => {
              toast.success(t('shell.signedOut'));
              navigate('/login');
            });
          }}
        >
          <LogOut aria-hidden="true" />
          {t('shell.signOut')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
