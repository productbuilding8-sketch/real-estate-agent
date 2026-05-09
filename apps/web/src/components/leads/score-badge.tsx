import { cn } from "@/lib/cn";

interface ScoreBadgeProps {
  score: number | null;
  className?: string;
}

export function ScoreBadge({ score, className }: ScoreBadgeProps) {
  if (score === null) {
    return <span className={cn("text-xs text-gray-400", className)}>—</span>;
  }

  const config =
    score >= 71
      ? { text: "text-emerald-700", bg: "bg-emerald-50", ring: "ring-emerald-200/60", bar: "bg-emerald-500" }
      : score >= 41
      ? { text: "text-amber-700",   bg: "bg-amber-50",   ring: "ring-amber-200/60",   bar: "bg-amber-400"   }
      : { text: "text-red-700",     bg: "bg-red-50",     ring: "ring-red-200/60",     bar: "bg-red-400"     };

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center min-w-[2.25rem] h-6 rounded-full px-1.5 text-xs font-bold ring-1 ring-inset tabular-nums",
        config.text, config.bg, config.ring,
        className,
      )}
    >
      {score}
    </span>
  );
}
