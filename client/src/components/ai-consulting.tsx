"use client";

// import { EarningsSection } from "@/components/ai/earnings-section";
// import { PerSection } from "@/components/ai/per-section";
// import { ReportSection } from "@/components/ai/report-section";
import { StocksSection } from "@/components/ai/stocks-section";

export function AiConsulting() {
  return (
    <section>
      <h1 className="text-xl font-bold text-gray-900 mb-4">
        AI×コンサル銘柄分析
      </h1>

      <div className="mb-4">
        <p className="text-lg font-medium text-black">類似企業分析</p>
      </div>

      <StocksSection />
    </section>
  );
}
