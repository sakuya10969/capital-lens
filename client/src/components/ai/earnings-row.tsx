import { useState } from "react";

import { Note } from "@/components/ai/note";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import { changeColor, fmt } from "@/lib/formatters";
import type { EarningsItem } from "@/types/ai_consulting";

export function EarningsRow({ item }: { item: EarningsItem }) {
  const [expanded, setExpanded] = useState<boolean>(false);
  return (
    <>
      <TableRow>
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
        <TableCell className="font-mono text-gray-600">{item.symbol}</TableCell>
        <TableCell className="text-gray-700">
          {item.earnings_date ?? "—"}
        </TableCell>
        <TableCell
          className={`text-right ${changeColor(item.price_change_5d)}`}
        >
          {item.price_change_5d != null
            ? `${item.price_change_5d > 0 ? "+" : ""}${fmt(item.price_change_5d)}%`
            : "—"}
        </TableCell>
        <TableCell
          className={`text-right ${changeColor(item.price_change_1m)}`}
        >
          {item.price_change_1m != null
            ? `${item.price_change_1m > 0 ? "+" : ""}${fmt(item.price_change_1m)}%`
            : "—"}
        </TableCell>
        <TableCell className="text-right">
          {item.trailing_pe != null ? `${fmt(item.trailing_pe, 1)}x` : "—"}
        </TableCell>
        <TableCell>
          {item.summary ? (
            <Button
              onClick={() => setExpanded((v) => !v)}
              variant="link"
              size="sm"
              className="h-auto whitespace-nowrap px-0 text-xs text-blue-600"
            >
              {expanded ? "閉じる" : "概要を見る"}
            </Button>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
          <Note text={item.note} />
        </TableCell>
      </TableRow>
      {expanded && item.summary && (
        <TableRow className="bg-blue-50/40">
          <TableCell
            colSpan={7}
            className="text-sm text-gray-700 leading-relaxed py-3 px-6"
          >
            {item.summary}
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
