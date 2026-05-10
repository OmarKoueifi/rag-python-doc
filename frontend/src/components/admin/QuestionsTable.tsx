import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, ShieldOff } from "lucide-react";
import clsx from "clsx";

import { getQuestion, listQuestions } from "../../lib/api";
import type {
  QuestionDetail,
  QuestionSummary,
  SourceRef,
} from "../../lib/types";

const PAGE_SIZE = 10;

export function QuestionsTable() {
  const [items, setItems] = useState<QuestionSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blockedOnly, setBlockedOnly] = useState(false);
  const [sessionFilter, setSessionFilter] = useState("");
  const [expanded, setExpanded] = useState<Record<number, QuestionDetail>>({});

  useEffect(() => {
    setLoading(true);
    listQuestions({
      limit: PAGE_SIZE,
      offset,
      blocked: blockedOnly ? true : undefined,
      session_id: sessionFilter || undefined,
    })
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [offset, blockedOnly, sessionFilter]);

  const toggleRow = async (id: number) => {
    if (expanded[id]) {
      setExpanded(({ [id]: _removed, ...rest }) => rest);
      return;
    }
    const detail = await getQuestion(id);
    setExpanded((prev) => ({ ...prev, [id]: detail }));
  };

  return (
    <div className="rounded-xl border border-ink-200 bg-white">
      <div className="p-4 flex items-center justify-between flex-wrap gap-3">
        <h2 className="font-semibold text-ink-900">Recent questions</h2>
        <div className="flex items-center gap-2 text-sm">
          <input
            type="text"
            value={sessionFilter}
            onChange={(e) => {
              setOffset(0);
              setSessionFilter(e.target.value);
            }}
            placeholder="Filter by session ID…"
            className="rounded-md border border-ink-200 px-2.5 py-1.5 text-xs outline-none focus:border-accent-500 w-56"
          />
          <label className="flex items-center gap-1.5 text-ink-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={blockedOnly}
              onChange={(e) => {
                setOffset(0);
                setBlockedOnly(e.target.checked);
              }}
            />
            Blocked only
          </label>
        </div>
      </div>

      {error && (
        <div className="px-4 pb-3 text-sm text-red-600">Error: {error}</div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-wide text-ink-500 bg-ink-50 border-y border-ink-200">
            <tr>
              <th className="py-2 px-3 w-6"></th>
              <th className="py-2 px-3 text-left w-36">When</th>
              <th className="py-2 px-3 text-left">Question</th>
              <th className="py-2 px-3 text-left w-24">Retrieved</th>
              <th className="py-2 px-3 text-left w-20">Mean sim</th>
              <th className="py-2 px-3 text-left w-24">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-ink-400">
                  Loading…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-ink-400">
                  No questions match these filters.
                </td>
              </tr>
            ) : (
              items.map((q) => (
                <RowWithDetail
                  key={q.id}
                  q={q}
                  detail={expanded[q.id]}
                  onToggle={() => toggleRow(q.id)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        offset={offset}
        total={total}
        pageSize={PAGE_SIZE}
        onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
        onNext={() =>
          offset + PAGE_SIZE < total && setOffset(offset + PAGE_SIZE)
        }
      />
    </div>
  );
}

function RowWithDetail({
  q,
  detail,
  onToggle,
}: {
  q: QuestionSummary;
  detail?: QuestionDetail;
  onToggle: () => void;
}) {
  return (
    <>
      <tr
        className={clsx(
          "border-b border-ink-100 hover:bg-ink-50 cursor-pointer",
          q.moderation_blocked && "bg-red-50/40",
        )}
        onClick={onToggle}
      >
        <td className="py-2 px-3 align-top">
          {detail ? (
            <ChevronDown className="w-4 h-4 text-ink-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-ink-400" />
          )}
        </td>
        <td className="py-2 px-3 align-top text-ink-500 whitespace-nowrap">
          {formatWhen(q.created_at)}
        </td>
        <td className="py-2 px-3 align-top">
          <div className="text-ink-900 line-clamp-2">{q.question}</div>
          <div className="text-xs text-ink-400 font-mono truncate">
            {q.session_id}
          </div>
        </td>
        <td className="py-2 px-3 align-top text-ink-600 tabular-nums">
          {q.retrieval_count}
        </td>
        <td className="py-2 px-3 align-top tabular-nums">
          {q.avg_similarity !== null ? q.avg_similarity.toFixed(3) : "—"}
        </td>
        <td className="py-2 px-3 align-top">
          {q.moderation_blocked ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-medium">
              <ShieldOff className="w-3 h-3" /> blocked
            </span>
          ) : (
            <span className="inline-flex rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs font-medium">
              answered
            </span>
          )}
        </td>
      </tr>
      {detail && (
        <tr className="border-b border-ink-100 bg-ink-50/60">
          <td></td>
          <td colSpan={5} className="py-3 px-3">
            <QuestionDetailView detail={detail} />
          </td>
        </tr>
      )}
    </>
  );
}

function QuestionDetailView({ detail }: { detail: QuestionDetail }) {
  return (
    <div className="space-y-3 text-sm">
      {detail.answer && (
        <div>
          <div className="text-xs uppercase tracking-wide text-ink-500 mb-1">
            Answer
          </div>
          <div className="rounded-lg bg-white border border-ink-200 p-3 whitespace-pre-wrap text-ink-800 text-[13px] leading-relaxed">
            {detail.answer}
          </div>
        </div>
      )}
      {detail.sources.length > 0 && <SourcesListInline sources={detail.sources} />}
    </div>
  );
}

function SourcesListInline({ sources }: { sources: SourceRef[] }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-ink-500 mb-1">
        Retrieved sources
      </div>
      <ul className="space-y-1">
        {sources.map((s) => (
          <li key={s.rank} className="flex items-start gap-2 text-[13px]">
            <span className="flex-shrink-0 font-mono text-ink-400 w-5">
              [{s.rank}]
            </span>
            <div className="min-w-0 flex-1">
              <a
                href={s.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-600 hover:text-accent-700 underline decoration-accent-200 hover:decoration-accent-500"
              >
                {s.heading_path}
              </a>
              <span className="ml-2 text-ink-400 font-mono">{s.module}</span>
              <span className="ml-2 text-ink-400 tabular-nums">
                sim {s.similarity.toFixed(3)}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Pagination({
  offset,
  total,
  pageSize,
  onPrev,
  onNext,
}: {
  offset: number;
  total: number;
  pageSize: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + pageSize, total);
  return (
    <div className="flex items-center justify-between px-4 py-3 text-sm text-ink-500">
      <span>
        {from}–{to} of {total}
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPrev}
          disabled={offset === 0}
          className="rounded-md border border-ink-200 px-2.5 py-1 disabled:opacity-40 hover:bg-ink-50"
        >
          ← Prev
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={offset + pageSize >= total}
          className="rounded-md border border-ink-200 px-2.5 py-1 disabled:opacity-40 hover:bg-ink-50"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const mins = Math.round((now.getTime() - d.getTime()) / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 14) return `${days}d ago`;
  return d.toLocaleDateString();
}
