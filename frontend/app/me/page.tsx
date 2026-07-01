'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ClearanceBadge } from '@/components/ClearanceBadge';
import { TopNav } from '@/components/TopNav';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { initials } from '@/lib/initials';
import type { UserSummary } from '@/lib/types';

import { DemoQuestions } from './components/DemoQuestions';
import { RecentQueries } from './components/RecentQueries';

function tenantAcronym(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');
}

export default function MePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => router.replace('/login'))
      .finally(() => setLoading(false));
  }, [router]);

  async function onLogout() {
    await api.logout();
    router.replace('/login');
  }

  if (loading) return <main className="p-8 text-muted-foreground">Loading…</main>;
  if (!user) return null;

  const isAdmin = user.role === 'director' || user.role === 'executive';

  return (
    <>
      <TopNav user={{ username: user.username, role: user.role, max_clearance: user.max_clearance }} />
      <main className="mx-auto max-w-5xl p-4 sm:p-8 space-y-6">
        {/* Identity hero card */}
        <div className="bg-card border border-border rounded-lg p-6">
          <div className="flex items-start gap-4">
            <div
              className="w-14 h-14 rounded-lg grid place-items-center text-primary-foreground font-mono text-[16px] font-semibold shrink-0"
              style={{
                background:
                  'linear-gradient(135deg, oklch(0.52 0.16 264) 0%, oklch(0.40 0.14 264) 100%)',
              }}
              aria-hidden
            >
              {initials(user.username)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[19px] font-semibold leading-tight truncate">
                {user.tenant.role_label}: {user.username}
              </div>
              <div className="text-[13px] text-muted-foreground">{user.tenant.name}</div>
            </div>
            <div
              className="hidden sm:grid w-12 h-12 rounded-md bg-muted border border-border place-items-center font-mono text-[11px] font-semibold text-muted-foreground shrink-0"
              aria-hidden
            >
              {tenantAcronym(user.tenant.name) || '—'}
            </div>
          </div>

          <div className="h-px bg-border my-5" aria-hidden />

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Max clearance
              </dt>
              <dd>
                <ClearanceBadge classification={user.max_clearance} />
              </dd>
            </div>
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Departments
              </dt>
              <dd className="text-[13px] font-medium">
                {user.departments.join(', ') || '—'}
              </dd>
            </div>
            <div>
              <dt className="text-[10px] font-mono uppercase tracking-[0.08em] text-subtle mb-1">
                Tier
              </dt>
              <dd className="text-[13px] font-medium capitalize">{user.role}</dd>
            </div>
          </dl>

          <div className="flex flex-wrap items-center gap-2 mt-5">
            <Button onClick={() => router.push('/chat')}>Open chat</Button>
            {isAdmin && (
              <Button variant="secondary" onClick={() => router.push('/admin/audit')}>
                View audit log
              </Button>
            )}
            <Button
              variant="outline"
              onClick={onLogout}
              className="hover:text-destructive hover:border-destructive/40"
            >
              Sign out
            </Button>
          </div>
        </div>

        {/* Lower grid */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1.15fr] gap-4">
          <RecentQueries />
          <DemoQuestions departments={user.departments} />
        </div>
      </main>
    </>
  );
}
