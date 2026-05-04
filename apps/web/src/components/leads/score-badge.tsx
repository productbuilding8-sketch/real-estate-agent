import { cn } from "@/lib/cn";

interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score === null) {
    return <span className={cn("text-xs text-gray-400", className)}>—</span>;
  }

  const color =
    score >= 71 ? "text-emerald-700 bg-emerald-50 ring-emerald-200" :
    score >= 41 ? "text-amber-700 bg-amber-50 ring-amber-200" :
                  "text-red-700 bg-red-50 ring-red-200";

  return (
    <span className={cn(
      "inline-flex items-center justify-center w-9 h-6 rounded-full text-xs font-bold ring-1 ring-inset tabular-nums",
      color, className,
    )}>
      {score}
    </span>
  );
}
