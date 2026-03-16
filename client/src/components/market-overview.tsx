import { Section } from "@/components/market/section";
import type { MarketOverviewResponse } from "@/types/market";

export function MarketOverview({ data }: { data: MarketOverviewResponse }) {
  return (
    <section>
      <div className="flex items-baseline justify-between mb-4">
        <h1 className="text-xl font-bold text-gray-900">
          資本市場ダッシュボード
        </h1>
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
