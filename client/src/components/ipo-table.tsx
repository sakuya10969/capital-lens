"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { IpoRow } from "@/components/ipo/ipo-row";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getIpoLatest, getIpoSummary } from "@/lib/api/ipo";
import type { LoadState } from "@/types/common";
import type { IpoItem, IpoSummaryResponse } from "@/types/ipo";

export function IpoTable() {
  const [items, setItems] = useState<IpoItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [listStatus, setListStatus] = useState<"loading" | "error" | "done">(
    "loading",
  );

  const [summaries, setSummaries] = useState<
    Map<string, LoadState<IpoSummaryResponse>>
  >(() => new Map());
  const [openRows, setOpenRows] = useState<Set<string>>(() => new Set());

  const abortRef = useRef<AbortController | null>(null);

  const fetchList = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setListStatus("loading");
    try {
      const data = await getIpoLatest(controller.signal);
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
      const data = await getIpoSummary(code);
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
          const s = summaries.get(code);
          if (!s || s.status === "error") {
            fetchSummary(code);
          }
        }
        return next;
      });
    },
    [summaries, fetchSummary],
  );

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
          <Button
            onClick={fetchList}
            variant="ghost"
            size="sm"
            className="h-auto bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 hover:text-red-700"
          >
            <RefreshCw className="w-3 h-3" />
            再試行
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900">直近IPO一覧</h1>
        <span className="text-xs text-black">{totalCount} 件</span>
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
                  summaryState={
                    summaries.get(item.ticker) ?? { status: "idle" }
                  }
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
