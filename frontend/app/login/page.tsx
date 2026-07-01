'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import {
  ArrowRight,
  Building2,
  Database,
  Eye,
  EyeOff,
  FileText,
  GitCompareArrows,
  KeyRound,
  User as UserIcon,
} from 'lucide-react';

import { api } from '@/lib/api';

import { DemoAccountPicker } from './components/DemoAccountPicker';

function fieldClasses(): string {
  return (
    'w-full h-10 pl-9 pr-3 rounded-md bg-card border border-border-strong text-sm ' +
    'focus:outline-none focus:border-primary focus:ring-[3px] focus:ring-accent transition'
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [tenantId, setTenantId] = useState(process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ?? '');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [selectedDemo, setSelectedDemo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const usernameRef = useRef<HTMLInputElement | null>(null);

  function pickDemo(u: string, p: string) {
    setUsername(u);
    setPassword(p);
    setSelectedDemo(u);
    setError(null);
  }

  function chooseCustom() {
    setUsername('');
    setPassword('');
    setSelectedDemo(null);
    setError(null);
    usernameRef.current?.focus();
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.login(tenantId.trim(), username.trim(), password);
      router.push('/me');
    } catch (err) {
      const msg = (err as { detail?: string })?.detail ?? 'login failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-muted flex items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-5xl bg-card border border-border rounded-lg overflow-hidden shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 min-h-[560px]">
          {/* Left: branded panel */}
          <div
            className="relative p-10 text-primary-foreground flex flex-col justify-between"
            style={{
              background:
                'linear-gradient(155deg, oklch(0.28 0.05 264) 0%, oklch(0.22 0.03 257) 100%)',
            }}
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.14]"
              style={{
                backgroundImage:
                  'radial-gradient(circle at center, oklch(0.985 0.004 247) 1px, transparent 1.5px)',
                backgroundSize: '22px 22px',
              }}
              aria-hidden
            />
            <div className="relative">
              <div className="flex items-center gap-2 font-mono text-[13px] font-semibold tracking-[0.18em]">
                <div className="w-8 h-8 rounded-md bg-primary/60 grid place-items-center">
                  <Database className="w-4 h-4" aria-hidden />
                </div>
                HOLOCRON
              </div>
              <h1 className="mt-8 text-[26px] font-semibold leading-tight tracking-[-0.015em] max-w-md">
                Imperial Knowledge Assistant
              </h1>
              <p className="mt-3 text-[14px] leading-relaxed max-w-md text-primary-foreground/85">
                Ask a question. Cite it. See conflicts. Refuse when you must.
                One clearance-aware assistant across every department.
              </p>
            </div>
            <div className="relative flex flex-wrap gap-2 mt-6">
              <FeaturePill icon={<FileText className="w-3.5 h-3.5" aria-hidden />} label="Cited sources" />
              <FeaturePill icon={<GitCompareArrows className="w-3.5 h-3.5" aria-hidden />} label="Conflict detection" />
            </div>
          </div>

          {/* Right: form panel */}
          <div className="p-8 sm:p-10 bg-card">
            <h2 className="text-[18px] font-semibold mb-6">Sign in</h2>
            <form className="space-y-4" onSubmit={onSubmit}>
              <FieldWrapper label="Tenant ID" htmlFor="tenant">
                <Building2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  id="tenant"
                  value={tenantId}
                  onChange={(e) => setTenantId(e.target.value)}
                  placeholder="Tenant UUID"
                  required
                  className={`${fieldClasses()} font-mono text-[12px]`}
                />
              </FieldWrapper>
              <FieldWrapper label="Username" htmlFor="username">
                <UserIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  ref={usernameRef}
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. executive.fleet"
                  required
                  className={fieldClasses()}
                />
              </FieldWrapper>
              <FieldWrapper label="Password" htmlFor="password">
                <KeyRound className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className={`${fieldClasses()} pr-9`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </FieldWrapper>
              {error && <p className="text-[12px] text-destructive">{error}</p>}
              <button
                type="submit"
                disabled={submitting}
                className="w-full h-10 rounded-md bg-foreground text-background text-[13px] font-medium flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-60 transition"
              >
                {submitting ? 'Signing in…' : (
                  <>
                    Sign in <ArrowRight className="w-4 h-4" aria-hidden />
                  </>
                )}
              </button>
              <div className="flex items-center justify-between text-[11px] font-mono text-subtle mt-2">
                <span>demo password: imperial-march</span>
              </div>
            </form>
          </div>
        </div>

        {/* Demo picker footer */}
        <DemoAccountPicker
          selected={selectedDemo}
          onPick={pickDemo}
          onCustom={chooseCustom}
        />
      </div>
    </main>
  );
}

function FeaturePill({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-primary/40 text-primary-foreground text-[12px] font-mono uppercase tracking-[0.08em]">
      {icon}
      {label}
    </div>
  );
}

function FieldWrapper({
  htmlFor,
  label,
  children,
}: {
  htmlFor: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={htmlFor}
        className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted-foreground"
      >
        {label}
      </label>
      <div className="relative">{children}</div>
    </div>
  );
}
