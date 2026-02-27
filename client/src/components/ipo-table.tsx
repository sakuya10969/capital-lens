"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Loader2, RefreshCw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { IpoItem, IpoLatestResponse, IpoSummaryResponse } from "@/types/ipo";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SummaryState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error" }
  | { status: "done"; data: IpoSummaryResponse };

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

// ------------------------------------------------------------------ //
// IpoTable: 一覧フェッチ（エラー/retry含む）+ 行ごとオンデマンド要約  //
// ------------------------------------------------------------------ //

export function IpoTable() {
  const [items, setItems] = useState<IpoItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [listStatus, setListStatus] = useState<"loading" | "error" | "done">("loading");

  // code -> SummaryState のクライアントサイドキャッシュ
  const [summaries, setSummaries] = useState<Map<string, SummaryState>>(
    () => new Map()
  );
  // 展開中の行コードセット
  const [openRows, setOpenRows] = useState<Set<string>>(() => new Set());

  const abortRef = useRef<AbortController | null>(null);

  const fetchList = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setListStatus("loading");
    try {
      const res = await fetch(`${API_URL}/api/ipo/latest`, {
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: IpoLatestResponse = await res.json();
      setItems(data.items);
      setTotalCount(data.total_count);
      setListStatus("done");
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setListStatus("error");
    }
  }, []);

  useEffect(() => {
    fetchList();
    return () => abortRef.current?.abort();
  }, [fetchList]);

  const fetchSummary = useCallback(async (code: string) => {
    setSummaries((prev) => new Map(prev).set(code, { status: "loading" }));
    try {
      const res = await fetch(`${API_URL}/api/ipo/${code}/summary`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: IpoSummaryResponse = await res.json();
      setSummaries((prev) => new Map(prev).set(code, { status: "done", data }));
    } catch {
      setSummaries((prev) => new Map(prev).set(code, { status: "error" }));
    }
  }, []);

  const handleToggle = useCallback(
    (code: string) => {
      setOpenRows((prev) => {
        const next = new Set(prev);
        if (next.has(code)) {
          next.delete(code);
        } else {
          next.add(code);
          // 未取得 or エラーのときだけフェッチ
          const s = summaries.get(code);
          if (!s || s.status === "error") {
            fetchSummary(code);
          }
        }
        return next;
      });
    },
    [summaries, fetchSummary]
  );

  // ---- レンダリング分岐 -------------------------------------------- //

  if (listStatus === "loading") {
    return (
      <section>
        <h1 className="text-xl font-bold text-gray-900 mb-4">直近IPO一覧</h1>
        <div className="flex items-center justify-center gap-2 py-16 text-gray-400 text-sm">
          <Loader2 className="animate-spin w-4 h-4" />
          読み込み中...
        </div>
      </section>
    );
  }

  if (listStatus === "error") {
    return (
      <section>
        <h1 className="text-xl font-bold text-gray-900 mb-4">直近IPO一覧</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center space-y-3">
          <p className="text-red-600 text-sm">
            IPO一覧の取得に失敗しました。バックエンドサーバーが起動しているか確認してください。
          </p>
          <button
            onClick={fetchList}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium
                       bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            再試行
          </button>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900">直近IPO一覧</h1>
        <span className="text-xs text-gray-400">{totalCount} 件</span>
      </div>

      {items.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          現在表示できるIPO情報がありません。
        </p>
      ) : (
        <div className="rounded-lg border border-gray-200 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>上場日</TableHead>
                <TableHead>企業名</TableHead>
                <TableHead>コード</TableHead>
                <TableHead>市場</TableHead>
                <TableHead className="text-right">想定価格</TableHead>
                <TableHead className="w-28" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <IpoRow
                  key={`${item.ticker}-${item.listing_date}`}
                  item={item}
                  isOpen={openRows.has(item.ticker)}
                  summaryState={summaries.get(item.ticker) ?? { status: "idle" }}
                  onToggle={handleToggle}
                  onRetry={fetchSummary}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}

// ------------------------------------------------------------------ //
// IpoRow: 行 + アコーディオン要約                                      //
// ------------------------------------------------------------------ //

function IpoRow({
  item,
  isOpen,
  summaryState,
  onToggle,
  onRetry,
}: {
  item: IpoItem;
  isOpen: boolean;
  summaryState: SummaryState;
  onToggle: (code: string) => void;
  onRetry: (code: string) => void;
}) {
  return (
    <>
      <TableRow>
        <TableCell className="whitespace-nowrap text-gray-500">
          {formatDate(item.listing_date)}
        </TableCell>
        <TableCell className="font-medium text-gray-900">
          {item.company_name}
        </TableCell>
        <TableCell className="text-gray-600 font-mono">{item.ticker}</TableCell>
        <TableCell className="text-gray-600">{item.market}</TableCell>
        <TableCell className="text-right text-gray-900">
          {item.offering_price != null
            ? `¥${item.offering_price.toLocaleString("ja-JP")}`
            : "—"}
        </TableCell>
        <TableCell>
          <button
            onClick={() => onToggle(item.ticker)}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium
                       text-blue-600 bg-blue-50 hover:bg-blue-100 transition-colors whitespace-nowrap"
            aria-expanded={isOpen}
          >
            要約を見る
            {isOpen ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </button>
        </TableCell>
      </TableRow>

      {isOpen && (
        <TableRow className="bg-blue-50/40">
          <TableCell colSpan={6} className="py-4 px-6">
            <SummaryPanel
              code={item.ticker}
              state={summaryState}
              onRetry={onRetry}
            />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

// ------------------------------------------------------------------ //
// SummaryPanel: ローディング / エラー / 要約表示                       //
// ------------------------------------------------------------------ //

function SummaryPanel({
  code,
  state,
  onRetry,
}: {
  code: string;
  state: SummaryState;
  onRetry: (code: string) => void;
}) {
  if (state.status === "idle" || state.status === "loading") {
    return (
      <div className="flex items-center gap-2 text-gray-400 text-sm">
        <Loader2 className="animate-spin w-4 h-4" />
        要約を読み込み中...
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="text-red-500">要約の取得に失敗しました。</span>
        <button
          onClick={() => onRetry(code)}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium
                     text-red-600 bg-red-100 hover:bg-red-200 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          再試行
        </button>
      </div>
    );
  }

  const { data } = state;
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-blue-700">会社概要</span>
        {data.cached && (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            キャッシュ
          </span>
        )}
      </div>
      <ul className="space-y-1">
        {data.bullets.map((bullet, i) => (
          <li key={i} className="flex gap-2 text-sm text-gray-700">
            <span className="text-blue-400 mt-0.5 shrink-0">・</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
