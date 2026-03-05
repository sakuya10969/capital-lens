import { Minus, TrendingDown, TrendingUp } from "lucide-react";

export function ChangeIndicator({
  change,
  changePercent,
}: {
  change: number;
  changePercent: number;
}) {
  if (change > 0) {
    return (
      <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
        <TrendingUp size={14} />
        {change >= 1000
          ? `+${change.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`
          : `+${change.toFixed(2)}`} {" "}
        (+{changePercent.toFixed(2)}%)
      </span>
    );
  }
  if (change < 0) {
    return (
      <span className="flex items-center gap-1 text-red-500 text-sm font-medium">
        <TrendingDown size={14} />
        {change >= -1000
          ? change.toFixed(2)
          : change.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}{" "}
        ({changePercent.toFixed(2)}%)
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-gray-400 text-sm">
      <Minus size={14} />
      0.00 (0.00%)
    </span>
  );
}
