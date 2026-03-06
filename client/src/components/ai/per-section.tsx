import { useCallback, useEffect, useState } from "react";

import { ErrorRow } from "@/components/ai/error-row";
import { LoadingRow } from "@/components/ai/loading-row";
import { Note } from "@/components/ai/note";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getAiConsultingPer } from "@/lib/api/ai-consulting";
import { fmt } from "@/lib/formatters";
import type { LoadState } from "@/types/common";
import type { PerResponse } from "@/types/ai_consulting";

export function PerSection() {
  const [state, setState] = useState<LoadState<PerResponse>>({
    status: "loading",
  });

  const fetch_ = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await getAiConsultingPer();
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
    <div>
      <p className="text-xs text-gray-400 mb-3">
        基準日時: {new Date(data.as_of).toLocaleString("ja-JP")}
      </p>
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
                item.pe_used === "trailing"
                  ? item.trailing_pe
                  : item.pe_used === "forward"
                    ? item.forward_pe
                    : item.pe_used === "computed"
                      ? item.computed_pe
                      : null;
              return (
                <TableRow key={item.symbol}>
                  <TableCell className="font-medium text-gray-900">
                    {item.website ? (
                      <a
                        href={item.website}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-600 hover:underline"
                      >
                        {item.name}
                      </a>
                    ) : (
                      item.name
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-gray-600">
                    {item.symbol}
                  </TableCell>
                  <TableCell className="text-right text-gray-900">
                    {pe != null
                      ? `${item.currency ?? ""} ${fmt(item.price)}`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right text-gray-900 font-medium">
                    {pe != null ? `${fmt(pe, 1)}x` : "—"}
                  </TableCell>
                  <TableCell className="text-gray-500 text-xs">
                    {item.pe_used ?? "—"}
                  </TableCell>
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
