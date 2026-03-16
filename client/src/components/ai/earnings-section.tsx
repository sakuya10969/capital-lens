import { useCallback, useEffect, useState } from "react";

import { EarningsRow } from "@/components/ai/earnings-row";
import { ErrorRow } from "@/components/ai/error-row";
import { LoadingRow } from "@/components/ai/loading-row";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getAiConsultingEarnings } from "@/lib/api/ai-consulting";
import type { LoadState } from "@/types/common";
import type { EarningsResponse } from "@/types/ai_consulting";

export function EarningsSection() {
  const [state, setState] = useState<LoadState<EarningsResponse>>({
    status: "loading",
  });

  const fetch_ = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await getAiConsultingEarnings();
      setState({ status: "done", data });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  useEffect(() => {
    fetch_();
  }, [fetch_]);

  if (state.status === "idle" || state.status === "loading") {
    return <LoadingRow />;
  }
  if (state.status === "error") {
    return <ErrorRow onRetry={fetch_} />;
  }

  const { data } = state;
  return (
    <div className="space-y-6">
      <p className="text-xs text-gray-400">
        対象期間: {data.window.from_date} 〜 {data.window.to_date}（±
        {data.window.days}日）
      </p>

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          決算予定銘柄{" "}
          <span className="text-blue-600">({data.upcoming.length}件)</span>
        </h3>
        {data.upcoming.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">
            期間内の決算予定銘柄なし
          </p>
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

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          決算日未取得 / 範囲外{" "}
          <span className="text-gray-400">({data.unknown.length}件)</span>
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
