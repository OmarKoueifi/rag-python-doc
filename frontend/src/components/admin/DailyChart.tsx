import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DailyCount } from "../../lib/types";

export function DailyChart({ data }: { data: DailyCount[] }) {
  const filled = fill14Days(data);
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="font-semibold text-ink-900">Questions per day</h2>
        <span className="text-xs text-ink-400">Last 14 days</span>
      </div>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filled} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f2" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 11, fill: "#8b929a" }}
              tickFormatter={formatShortDay}
              axisLine={false}
              tickLine={false}
              interval={1}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#8b929a" }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              cursor={{ fill: "#f7f8f9" }}
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #dde1e5",
                padding: "6px 10px",
              }}
              labelFormatter={(v: string) => v}
            />
            <Bar dataKey="count" fill="#2c6fff" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function fill14Days(data: DailyCount[]): DailyCount[] {
  const map = new Map(data.map((d) => [d.day, d.count]));
  const out: DailyCount[] = [];
  const today = new Date();
  for (let i = 13; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const day = d.toISOString().slice(0, 10);
    out.push({ day, count: map.get(day) ?? 0 });
  }
  return out;
}

function formatShortDay(d: string): string {
  // YYYY-MM-DD → M/D
  const [, m, dd] = d.split("-");
  if (!m || !dd) return d;
  return `${Number(m)}/${Number(dd)}`;
}
