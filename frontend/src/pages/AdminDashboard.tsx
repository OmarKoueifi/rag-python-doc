import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, RefreshCcw } from "lucide-react";

import { DailyChart } from "../components/admin/DailyChart";
import { FlaggedTable } from "../components/admin/FlaggedTable";
import { MetricsCards } from "../components/admin/MetricsCards";
import { QuestionsTable } from "../components/admin/QuestionsTable";
import { TopSourcesPanel } from "../components/admin/TopSources";
import { ApiError, adminLogout, adminMe, getMetrics } from "../lib/api";
import type { Metrics } from "../lib/types";

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const [authChecked, setAuthChecked] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminMe()
      .then((s) => {
        if (!s.authenticated) navigate("/admin/login", { replace: true });
        else setAuthChecked(true);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          navigate("/admin/login", { replace: true });
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      });
  }, [navigate]);

  useEffect(() => {
    if (!authChecked) return;
    getMetrics()
      .then(setMetrics)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [authChecked, refreshTick]);

  const onLogout = async () => {
    await adminLogout().catch(() => {
      /* ignore */
    });
    navigate("/admin/login", { replace: true });
  };

  if (!authChecked) {
    return (
      <div className="min-h-full flex items-center justify-center text-ink-400">
        Checking session…
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <header className="border-b border-ink-200 bg-white">
        <div className="mx-auto w-full max-w-6xl px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-ink-900 leading-tight">
              Admin dashboard
            </h1>
            <p className="text-xs text-ink-500 leading-tight">
              Observability for the Python docs RAG chat
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Link
              to="/"
              className="text-ink-500 hover:text-ink-800 underline decoration-ink-200 hover:decoration-ink-500"
            >
              Back to chat
            </Link>
            <button
              type="button"
              onClick={() => setRefreshTick((t) => t + 1)}
              className="rounded-md border border-ink-200 px-2.5 py-1.5 text-ink-600 hover:bg-ink-50 inline-flex items-center gap-1.5"
            >
              <RefreshCcw className="w-3.5 h-3.5" /> Refresh
            </button>
            <button
              type="button"
              onClick={onLogout}
              className="rounded-md border border-ink-200 px-2.5 py-1.5 text-ink-600 hover:bg-ink-50 inline-flex items-center gap-1.5"
            >
              <LogOut className="w-3.5 h-3.5" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 py-6 space-y-6">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {metrics ? (
          <>
            <MetricsCards metrics={metrics} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-2">
                <DailyChart data={metrics.questions_per_day} />
              </div>
              <div>
                <TopSourcesPanel sources={metrics.top_sources} />
              </div>
            </div>
          </>
        ) : (
          <div className="text-ink-400 text-sm">Loading metrics…</div>
        )}

        <QuestionsTable />
        <FlaggedTable />
      </main>
    </div>
  );
}
