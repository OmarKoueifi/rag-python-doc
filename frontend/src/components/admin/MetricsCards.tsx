import { AlertTriangle, MessageSquare, ShieldOff, Target } from "lucide-react";
import type { Metrics } from "../../lib/types";

export function MetricsCards({ metrics }: { metrics: Metrics }) {
  const cards = [
    {
      label: "Total questions",
      value: metrics.total_questions.toLocaleString(),
      icon: MessageSquare,
      tone: "ink",
    },
    {
      label: "Moderation blocks",
      value: metrics.total_blocked.toLocaleString(),
      icon: ShieldOff,
      tone: "red",
    },
    {
      label: "Flagged inputs",
      value: metrics.total_flagged.toLocaleString(),
      icon: AlertTriangle,
      tone: "amber",
    },
    {
      label: "Mean retrieval sim",
      value:
        metrics.mean_similarity !== null
          ? metrics.mean_similarity.toFixed(3)
          : "—",
      icon: Target,
      tone: "accent",
    },
  ] as const;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-xl border border-ink-200 bg-white p-4"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-500 uppercase tracking-wide">
              {c.label}
            </span>
            <c.icon className={`w-4 h-4 ${iconColor(c.tone)}`} />
          </div>
          <div className="mt-2 text-2xl font-semibold text-ink-900 tabular-nums">
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function iconColor(tone: "ink" | "red" | "amber" | "accent"): string {
  switch (tone) {
    case "red":
      return "text-red-500";
    case "amber":
      return "text-amber-500";
    case "accent":
      return "text-accent-500";
    case "ink":
      return "text-ink-400";
  }
}
