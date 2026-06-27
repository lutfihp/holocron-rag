import { Badge } from '@/components/ui/badge';
import type { ClearanceLevel } from '@/lib/types';

const COLORS: Record<ClearanceLevel, string> = {
  public: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  restricted: 'bg-amber-100 text-amber-800 border-amber-300',
  secret: 'bg-orange-100 text-orange-900 border-orange-300',
  top_secret: 'bg-red-100 text-red-900 border-red-300',
};

const LABELS: Record<ClearanceLevel, string> = {
  public: 'Public',
  restricted: 'Restricted',
  secret: 'Secret',
  top_secret: 'Top Secret',
};

export function ClearanceBadge({ level }: { level: ClearanceLevel }) {
  return (
    <Badge variant="outline" className={`border ${COLORS[level]} font-medium`}>
      {LABELS[level]}
    </Badge>
  );
}
