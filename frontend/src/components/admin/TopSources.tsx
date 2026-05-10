import type { TopSource } from "../../lib/types";

export function TopSourcesPanel({ sources }: { sources: TopSource[] }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-4">
      <h2 className="font-semibold text-ink-900 mb-3">Most retrieved sources</h2>
      {sources.length === 0 ? (
        <p className="text-sm text-ink-400">No retrievals yet.</p>
      ) : (
        <ul className="space-y-2">
          {sources.map((s) => (
            <li key={s.source_url} className="flex items-center gap-3">
              <div className="flex-shrink-0 w-8 text-center text-sm tabular-nums font-mono text-ink-500">
                {s.count}×
              </div>
              <div className="min-w-0 flex-1">
                <a
                  href={s.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[13px] text-accent-600 hover:text-accent-700 underline decoration-accent-200 hover:decoration-accent-500 truncate block"
                  title={s.heading_path}
                >
                  {s.heading_path}
                </a>
                <div className="text-xs text-ink-400 font-mono">{s.module}</div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
