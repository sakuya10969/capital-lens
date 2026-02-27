import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MarketItem, MarketOverviewResponse } from "@/types/market";

function formatPrice(value: number, name: string): string {
  // Yields and FX show fewer decimal places
  if (name.includes("利回り") || name.includes("USD/JPY")) {
    return value.toLocaleString("ja-JP", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  if (value < 100) {
    return value.toLocaleString("ja-JP", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return value.toLocaleString("ja-JP", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function ChangeIndicator({
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
          : `+${change.toFixed(2)}`}{" "}
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

function MarketCard({ item }: { item: MarketItem }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{item.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold text-gray-900 mb-1">
          {formatPrice(item.current_price, item.name)}
        </p>
        <ChangeIndicator
          change={item.change}
          changePercent={item.change_percent}
        />
      </CardContent>
    </Card>
  );
}

function Section({
  title,
  items,
}: {
  title: string;
  items: MarketItem[];
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h2 className="text-base font-semibold text-gray-700 mb-3">{title}</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {items.map((item) => (
          <MarketCard key={item.name} item={item} />
        ))}
      </div>
    </div>
  );
}

export function MarketOverview({ data }: { data: MarketOverviewResponse }) {
  const updatedAt = new Date(data.generated_at).toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900">資本市場ダッシュボード</h1>
        <span className="text-xs text-gray-400">更新: {updatedAt} JST</span>
      </div>
      <div className="space-y-6">
        <Section title="株価指数" items={data.indices} />
        <Section title="リスク指標" items={data.risk_indicators} />
        <Section title="債券" items={data.bonds} />
        <Section title="為替" items={data.fx} />
        <Section title="商品" items={data.commodities} />
      </div>
    </section>
  );
}
