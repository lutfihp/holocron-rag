'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ClearanceBadge } from '@/components/ClearanceBadge';
import { TopNav } from '@/components/TopNav';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import type { UserSummary } from '@/lib/types';

export default function MePage() {
  const router = useRouter();
  const [user, setUser] = useState<UserSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => router.replace('/login'))
      .finally(() => setLoading(false));
  }, [router]);

  async function onLogout() {
    await api.logout();
    router.replace('/login');
  }

  if (loading) return <main className="p-8">Loading…</main>;
  if (!user) return null;

  return (
    <>
      <TopNav user={{ username: user.username, role: user.role, max_clearance: user.max_clearance }} />
      <main className="mx-auto max-w-2xl p-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>{user.tenant.role_label}: {user.username}</CardTitle>
            <CardDescription>{user.tenant.name}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Max clearance:</span>
              <ClearanceBadge classification={user.max_clearance} />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Departments</p>
              <p className="font-medium">{user.departments.join(', ') || '—'}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <Button variant="outline" onClick={onLogout}>Sign out</Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
