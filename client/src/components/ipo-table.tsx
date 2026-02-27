import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { IpoLatestResponse } from "@/types/ipo";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function IpoTable({ data }: { data: IpoLatestResponse }) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900">直近IPO一覧</h1>
        <span className="text-xs text-gray-400">
          {data.total_count} 件
        </span>
      </div>

      {data.items.length === 0 ? (
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
                <TableHead className="hidden md:table-cell">概要</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((item) => (
                <TableRow key={`${item.ticker}-${item.listing_date}`}>
                  <TableCell className="whitespace-nowrap text-gray-500">
                    {formatDate(item.listing_date)}
                  </TableCell>
                  <TableCell className="font-medium text-gray-900">
                    {item.company_name}
                  </TableCell>
                  <TableCell className="text-gray-600 font-mono">
                    {item.ticker}
                  </TableCell>
                  <TableCell className="text-gray-600">{item.market}</TableCell>
                  <TableCell className="text-right text-gray-900">
                    {item.offering_price != null
                      ? `¥${item.offering_price.toLocaleString("ja-JP")}`
                      : "—"}
                  </TableCell>
                  <TableCell className="hidden md:table-cell text-gray-500 max-w-xs truncate">
                    {item.summary}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  );
}
