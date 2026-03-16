import { Section } from "@/components/market/section";
import type { MarketOverviewResponse } from "@/types/market";

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
        <h1 className="text-xl font-bold text-gray-900">
          資本市場ダッシュボード
        </h1>
        <span className="text-xs text-black">更新: {updatedAt} JST</span>
      </div>
      {data.summary && (
        <p className="mb-5 text-sm text-black leading-relaxed border-l-2 border-blue-300 pl-3">
          {data.summary}
        </p>
      )}
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
