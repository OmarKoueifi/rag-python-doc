import { useEffect, useState } from "react";
import clsx from "clsx";

import { listFlagged } from "../../lib/api";
import type { FlaggedRow } from "../../lib/types";

type Filter = "all" | "moderation" | "injection";

export function FlaggedTable() {
  const [rows, setRows] = useState<FlaggedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listFlagged(filter === "all" ? undefined : filter)
      .then((r) => {
        setRows(r.items);
        setTotal(r.total);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="rounded-xl border border-ink-200 bg-white">
      <div className="p-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-semibold text-ink-900">Flagged inputs</h2>
          <p className="text-xs text-ink-400 mt-0.5">
            Moderation blocks the request; injection patterns are logged for
            observability and <em>don't</em> block.
          </p>
        </div>
        <div className="flex items-center gap-1 p-0.5 rounded-lg bg-ink-100 text-sm">
          {(["all", "moderation", "injection"] as Filter[]).map((f) => (
            <button
              type="button"
              key={f}
              onClick={() => setFilter(f)}
              className={clsx(
                "rounded-md px-2.5 py-1 capitalize transition",
                filter === f
                  ? "bg-white text-ink-900 shadow-sm"
                  : "text-ink-500 hover:text-ink-800",
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="px-4 pb-3 text-sm text-red-600">Error: {error}</div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-ink-500 bg-ink-50 border-y border-ink-200">
            <tr>
              <th className="py-2 px-3 text-left w-36">When</th>
              <th className="py-2 px-3 text-left w-28">Type</th>
              <th className="py-2 px-3 text-left">Input & match</th>
              <th className="py-2 px-3 text-left w-24">Blocked?</th>
            </tr>
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-ink-400">
                  Loading…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-8 text-center text-ink-400">
                  No flagged inputs in this view.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="border-b border-ink-100 align-top">
                  <td className="py-2 px-3 text-ink-500 whitespace-nowrap">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={clsx(
                        "rounded-full px-2 py-0.5 text-xs font-medium",
                        r.flag_type === "moderation"
                          ? "bg-red-100 text-red-700"
                          : "bg-amber-100 text-amber-800",
                      )}
                    >
                      {r.flag_type}
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <div className="text-ink-900 line-clamp-2">
                      {r.question}
                    </div>
                    <div className="text-xs text-ink-500 font-mono mt-0.5">
                      {r.flag_detail}
                    </div>
                  </td>
                  <td className="py-2 px-3">
                    {r.blocked ? (
                      <span className="text-red-700 font-medium">yes</span>
                    ) : (
                      <span className="text-ink-400">no</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-2.5 text-xs text-ink-400 border-t border-ink-100">
        {total} total
      </div>
    </div>
  );
}
