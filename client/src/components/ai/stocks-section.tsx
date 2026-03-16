"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  addStock,
  deleteStock,
  listStocks,
  refreshAllStocks,
  refreshStock,
} from "@/lib/api/ai-consulting";
import type { StockRecord, StocksResponse } from "@/types/ai_consulting";

//ユーティリティ

/** 億円 or 億ドル表記 */
function fmtBillion(v: number | null): string {
  if (v == null) return "—";
  const oku = v / 1e8;
  if (Math.abs(oku) >= 10000) {
    return `${(oku / 10000).toLocaleString("ja-JP", { maximumFractionDigits: 1 })}兆`;
  }
  return `${oku.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}億`;
}

function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null, digits = 1): string {
  if (v == null) return "—";
  return v.toLocaleString("ja-JP", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

// コンポーネント

export function StocksSection() {
  const [stocks, setStocks] = useState<StockRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [refreshingAll, setRefreshingAll] = useState(false);
  const [refreshing, setRefreshing] = useState<Record<string, boolean>>({});
  const [deleting, setDeleting] = useState<Record<string, boolean>>({});
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listStocks();
      setStocks(res.stocks);
    } catch {
      setError("銘柄一覧の読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async () => {
    const code = input.trim();
    if (!code) return;
    setAdding(true);
    setError(null);
    try {
      const res: StocksResponse = await addStock(code);
      setStocks(res.stocks);
      setInput("");
      inputRef.current?.focus();
    } catch {
      setError(`「${code}」の追加に失敗しました`);
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (code: string) => {
    setDeleting((prev) => ({ ...prev, [code]: true }));
    try {
      const res = await deleteStock(code);
      setStocks(res.stocks);
    } catch {
      setError(`「${code}」の削除に失敗しました`);
    } finally {
      setDeleting((prev) => ({ ...prev, [code]: false }));
    }
  };

  const handleRefreshOne = async (code: string) => {
    setRefreshing((prev) => ({ ...prev, [code]: true }));
    try {
      const res = await refreshStock(code);
      setStocks(res.stocks);
    } catch {
      setError(`「${code}」の更新に失敗しました`);
    } finally {
      setRefreshing((prev) => ({ ...prev, [code]: false }));
    }
  };

  const handleRefreshAll = async () => {
    setRefreshingAll(true);
    setError(null);
    try {
      const res = await refreshAllStocks();
      setStocks(res.stocks);
    } catch {
      setError("全更新に失敗しました");
    } finally {
      setRefreshingAll(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 追加フォーム */}
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="銘柄コード (例: 7203 / AAPL)"
          className="border rounded px-3 py-1.5 text-sm text-black w-56 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          disabled={adding}
        />
        <Button
          onClick={handleAdd}
          disabled={adding || !input.trim()}
          className="h-auto bg-indigo-600 px-4 py-1.5 text-sm text-white hover:bg-indigo-700 cursor-pointer"
        >
          {adding ? "取得中…" : "追加"}
        </Button>
        <Button
          onClick={handleRefreshAll}
          disabled={refreshingAll || stocks.length === 0}
          variant="outline"
          className="h-auto px-4 py-1.5 text-sm text-black bg-white hover:text-black hover:bg-gray-100 cursor-pointer"
        >
          {refreshingAll ? "更新中…" : "全更新"}
        </Button>
      </div>

      {/* エラー表示 */}
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}

      {/* テーブル */}
      {loading ? (
        <p className="text-sm text-gray-400">読み込み中…</p>
      ) : stocks.length === 0 ? (
        <p className="text-sm text-gray-400">
          銘柄が登録されていません。上のフォームから追加してください。
        </p>
      ) : (
        <div className="rounded-lg border overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>銘柄コード</TableHead>
                <TableHead>企業名</TableHead>
                <TableHead className="text-right">企業価値</TableHead>
                <TableHead className="text-right">時価総額</TableHead>
                <TableHead className="text-right">PER</TableHead>
                <TableHead className="text-right">売上</TableHead>
                <TableHead className="text-right">営利</TableHead>
                <TableHead className="text-right">純利</TableHead>
                <TableHead className="text-right">配当利</TableHead>
                <TableHead className="text-right">ROE</TableHead>
                <TableHead className="text-right">自資本比</TableHead>
                <TableHead className="text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stocks.map((s) => (
                <TableRow key={s.symbol}>
                  <TableCell className="font-mono text-black whitespace-nowrap">
                    {s.symbol}
                  </TableCell>
                  <TableCell className="font-medium text-black whitespace-nowrap">
                    {s.name ?? "—"}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtBillion(s.enterprise_value)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtBillion(s.market_cap)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {s.per != null ? `${fmtNum(s.per)}倍` : "—"}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtBillion(s.revenue)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtBillion(s.operating_income)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtBillion(s.net_income)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtPct(s.dividend_yield)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtPct(s.roe)}
                  </TableCell>
                  <TableCell className="text-right text-black">
                    {fmtPct(s.equity_ratio)}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <div className="flex justify-end gap-1">
                      <Button
                        onClick={() => handleRefreshOne(s.code)}
                        disabled={refreshing[s.code]}
                        variant="outline"
                        size="sm"
                        className="h-auto px-2 py-1 text-sm text-indigo-600 bg-white hover:bg-gray-100 hover:text-indigo-600 cursor-pointer"
                        title="再取得"
                      >
                        {refreshing[s.code] ? "…" : "更新"}
                      </Button>
                      <Button
                        onClick={() => handleDelete(s.code)}
                        disabled={deleting[s.code]}
                        variant="outline"
                        size="sm"
                        className="h-auto px-2 py-1 text-sm text-red-500 bg-white hover:bg-gray-100 hover:text-red-500 cursor-pointer"
                        title="削除"
                      >
                        {deleting[s.code] ? "…" : "削除"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* 最終更新時刻 */}
      {stocks.length > 0 && stocks[0].updated_at && (
        <p className="text-xs text-black">
          最終更新: {new Date(stocks[0].updated_at).toLocaleString("ja-JP")}
        </p>
      )}
    </div>
  );
}
