import { ChevronDown, ChevronUp } from "lucide-react";

import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/formatters";
import type { LoadState } from "@/types/common";
import type { IpoItem, IpoSummaryResponse } from "@/types/ipo";

import { SummaryPanel } from "@/components/ipo/summary-panel";

export function IpoRow({
  item,
  isOpen,
  summaryState,
  onToggle,
  onRetry,
}: {
  item: IpoItem;
  isOpen: boolean;
  summaryState: LoadState<IpoSummaryResponse>;
  onToggle: (code: string) => void;
  onRetry: (code: string) => void;
}) {
  return (
    <>
      <TableRow>
        <TableCell className="whitespace-nowrap text-black">
          {formatDate(item.listing_date)}
        </TableCell>
        <TableCell className="font-medium text-black">
          {item.company_name}
        </TableCell>
        <TableCell className="text-black font-mono">{item.ticker}</TableCell>
        <TableCell className="text-black">{item.market}</TableCell>
        <TableCell className="text-right text-black">
          {item.offering_price != null
            ? `¥${item.offering_price.toLocaleString("ja-JP")}`
            : "—"}
        </TableCell>
        <TableCell>
          <Button
            onClick={() => onToggle(item.ticker)}
            variant="ghost"
            size="sm"
            className="h-auto whitespace-nowrap bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-600 hover:bg-blue-100 hover:text-blue-600"
            aria-expanded={isOpen}
          >
            会社概要を見る
            {isOpen ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </Button>
        </TableCell>
      </TableRow>

      {isOpen && (
        <TableRow className="bg-blue-50/40">
          <TableCell colSpan={6} className="py-4 px-6">
            <SummaryPanel
              code={item.ticker}
              companyUrl={item.company_url}
              outlinePdfUrl={item.outline_pdf_url}
              state={summaryState}
              onRetry={onRetry}
            />
          </TableCell>
        </TableRow>
      )}
    </>
  );
}
