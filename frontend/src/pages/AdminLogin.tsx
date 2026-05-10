import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock } from "lucide-react";

import { ApiError, adminLogin, adminMe } from "../lib/api";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    adminMe()
      .then((s) => {
        if (!cancelled && s.authenticated) navigate("/admin", { replace: true });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await adminLogin(password);
      navigate("/admin", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("Invalid password.");
      } else {
        setError(e instanceof Error ? e.message : "Login failed.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm bg-white rounded-2xl border border-ink-200 p-6 shadow-sm"
      >
        <div className="flex items-center gap-2 mb-5">
          <div className="w-8 h-8 rounded-lg bg-ink-900 flex items-center justify-center">
            <Lock className="w-4 h-4 text-accent-100" />
          </div>
          <h1 className="font-semibold text-ink-900">Admin sign in</h1>
        </div>

        <label className="block text-sm text-ink-600 mb-1.5" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoFocus
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-ink-200 px-3 py-2 outline-none focus:border-accent-500 focus:ring-2 focus:ring-accent-100"
          placeholder="••••••••"
          required
        />

        {error && (
          <p className="mt-2 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || !password}
          className="mt-4 w-full rounded-lg bg-accent-500 text-white px-3 py-2 hover:bg-accent-600 disabled:bg-ink-200 disabled:text-ink-400 transition"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="mt-4 text-xs text-ink-400 text-center">
          This dashboard shows every question asked of the chat and where
          retrieval struggles.
        </p>
      </form>
    </div>
  );
}
