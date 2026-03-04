"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { EarningsItem, EarningsResponse, PerResponse, ReportResponse } from "@/types/ai_consulting";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type LoadState<T> = { status: "idle" } | { status: "loading" } | { status: "error" } | { status: "done"; data: T };

function fmt(v: number | null | undefined, digits = 2): string {
  if (v == null) return "—";
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function Note({ text }: { text: string | null }) {
  if (!text) return null;
  return <span className="block text-xs text-gray-400 mt-0.5">{text}</span>;
}

// Tabs
type Tab = "per" | "earnings" | "report";

// PER Table
function PerSection() {
  const [state, setState] = useState<LoadState<PerResponse>>({ status: "loading" });

  const fetch_ = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch(`${API_URL}/api/ai-consulting/per`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setState({ status: "done", data: await res.json() });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  if (state.status === "idle" || state.status === "loading") return <LoadingRow />;
  if (state.status === "error") return <ErrorRow onRetry={fetch_} />;

  const { data } = state;
  return (
    <div>
      <p className="text-xs text-gray-400 mb-3">基準日時: {new Date(data.as_of).toLocaleString("ja-JP")}</p>
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>銘柄名</TableHead>
              <TableHead>Symbol</TableHead>
              <TableHead className="text-right">株価</TableHead>
              <TableHead className="text-right">PER</TableHead>
              <TableHead>PER種別</TableHead>
              <TableHead>Note</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((item) => {
              const pe =
                item.pe_used === "trailing" ? item.trailing_pe :
                item.pe_used === "forward" ? item.forward_pe :
                item.pe_used === "computed" ? item.computed_pe : null;
              return (
                <TableRow key={item.symbol}>
                  <TableCell className="font-medium text-gray-900">{item.name}</TableCell>
                  <TableCell className="font-mono text-gray-600">{item.symbol}</TableCell>
                  <TableCell className="text-right text-gray-900">
                    {pe != null ? `${item.currency ?? ""} ${fmt(item.price)}` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-gray-900 font-medium">
                    {pe != null ? `${fmt(pe, 1)}x` : "—"}
                  </TableCell>
                  <TableCell className="text-gray-500 text-xs">{item.pe_used ?? "—"}</TableCell>
                  <TableCell>
                    <Note text={item.note} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// Earnings
function EarningsSection() {
  const [state, setState] = useState<LoadState<EarningsResponse>>({ status: "loading" });

  const fetch_ = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch(`${API_URL}/api/ai-consulting/earnings`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setState({ status: "done", data: await res.json() });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  if (state.status === "idle" || state.status === "loading") return <LoadingRow />;
  if (state.status === "error") return <ErrorRow onRetry={fetch_} />;

  const { data } = state;
  return (
    <div className="space-y-6">
      <p className="text-xs text-gray-400">
        対象期間: {data.window.from_date} 〜 {data.window.to_date}（±{data.window.days}日）
      </p>

      {/* Upcoming */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          決算予定銘柄 <span className="text-blue-600">({data.upcoming.length}件)</span>
        </h3>
        {data.upcoming.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">期間内の決算予定銘柄なし</p>
        ) : (
          <div className="rounded-lg border border-blue-200 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>銘柄名</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>決算日</TableHead>
                  <TableHead className="text-right">5d変化(%)</TableHead>
                  <TableHead className="text-right">1m変化(%)</TableHead>
                  <TableHead className="text-right">PER</TableHead>
                  <TableHead>概要</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.upcoming.map((item) => (
                  <EarningsRow key={item.symbol} item={item} />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Unknown */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          決算日未取得 / 範囲外 <span className="text-gray-400">({data.unknown.length}件)</span>
        </h3>
        {data.unknown.length > 0 && (
          <div className="rounded-lg border border-gray-200 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>銘柄名</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>決算日</TableHead>
                  <TableHead className="text-right">5d変化(%)</TableHead>
                  <TableHead className="text-right">1m変化(%)</TableHead>
                  <TableHead className="text-right">PER</TableHead>
                  <TableHead>概要</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.unknown.map((item) => (
                  <EarningsRow key={item.symbol} item={item} />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}

function EarningsRow({ item }: { item: EarningsItem }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <TableRow>
        <TableCell className="font-medium text-gray-900">{item.name}</TableCell>
        <TableCell className="font-mono text-gray-600">{item.symbol}</TableCell>
        <TableCell className="text-gray-700">{item.earnings_date ?? "—"}</TableCell>
        <TableCell className={`text-right ${changeColor(item.price_change_5d)}`}>
          {item.price_change_5d != null ? `${item.price_change_5d > 0 ? "+" : ""}${fmt(item.price_change_5d)}%` : "—"}
        </TableCell>
        <TableCell className={`text-right ${changeColor(item.price_change_1m)}`}>
          {item.price_change_1m != null ? `${item.price_change_1m > 0 ? "+" : ""}${fmt(item.price_change_1m)}%` : "—"}
        </TableCell>
        <TableCell className="text-right">{item.trailing_pe != null ? `${fmt(item.trailing_pe, 1)}x` : "—"}</TableCell>
        <TableCell>
          {item.summary ? (
            <button
              onClick={() => setExpanded((v) => !v)}
              className="text-xs text-blue-600 hover:underline whitespace-nowrap"
            >
              {expanded ? "閉じる" : "概要を見る"}
            </button>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
          <Note text={item.note} />
        </TableCell>
      </TableRow>
      {expanded && item.summary && (
        <TableRow className="bg-blue-50/40">
          <TableCell colSpan={7} className="text-sm text-gray-700 leading-relaxed py-3 px-6">
            {item.summary}
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function changeColor(v: number | null): string {
  if (v == null) return "text-gray-500";
  if (v > 0) return "text-green-600";
  if (v < 0) return "text-red-500";
  return "text-gray-700";
}

// Report

function ReportSection() {
  const [state, setState] = useState<LoadState<ReportResponse>>({ status: "idle" });

  const generate = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const res = await fetch(`${API_URL}/api/ai-consulting/report`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setState({ status: "done", data: await res.json() });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  return (
    <div className="space-y-4">
      <button
        onClick={generate}
        disabled={state.status === "loading"}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium
                   hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {state.status === "loading" && <Loader2 className="animate-spin w-4 h-4" />}
        Generate Report
      </button>

      {state.status === "error" && (
        <p className="text-sm text-red-500">レポートの生成に失敗しました。再度お試しください。</p>
      )}

      {state.status === "done" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
              {state.data.text_report}
            </pre>
          </div>
          <details className="rounded-lg border border-gray-200">
            <summary className="px-4 py-2 text-sm text-gray-500 cursor-pointer select-none hover:bg-gray-50">
              生データを見る (JSON)
            </summary>
            <pre className="px-4 py-3 text-xs text-gray-600 overflow-auto max-h-96 whitespace-pre-wrap">
              {JSON.stringify({ per: state.data.per, earnings: state.data.earnings }, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

// Utility components
function LoadingRow() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-gray-400 text-sm">
      <Loader2 className="animate-spin w-4 h-4" />
      読み込み中...
    </div>
  );
}

function ErrorRow({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center space-y-3">
      <p className="text-red-600 text-sm">データの取得に失敗しました。</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium
                   bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        再試行
      </button>
    </div>
  );
}

// Main component
export function AiConsulting() {
  const [tab, setTab] = useState<Tab>("per");

  const tabs: { key: Tab; label: string }[] = [
    { key: "per", label: "PER一覧" },
    { key: "earnings", label: "決算期" },
    { key: "report", label: "レポート" },
  ];

  return (
    <section>
      <h1 className="text-xl font-bold text-gray-900 mb-4">AI×コンサル銘柄分析</h1>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors
              ${tab === key
                ? "border-b-2 border-indigo-600 text-indigo-600"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "per" && <PerSection />}
      {tab === "earnings" && <EarningsSection />}
      {tab === "report" && <ReportSection />}
    </section>
  );
}
