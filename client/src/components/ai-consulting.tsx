"use client";

import { useState } from "react";

import { EarningsSection } from "@/components/ai/earnings-section";
import { PerSection } from "@/components/ai/per-section";
import { ReportSection } from "@/components/ai/report-section";

type Tab = "per" | "earnings" | "report";

export function AiConsulting() {
  const [tab, setTab] = useState<Tab>("per");

  const tabs: { key: Tab; label: string }[] = [
    { key: "per", label: "PER一覧" },
    { key: "earnings", label: "決算期" },
    { key: "report", label: "レポート" },
  ];

  return (
    <section>
      <h1 className="text-xl font-bold text-gray-900 mb-4">
        AI×コンサル銘柄分析
      </h1>

      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium rounded-t transition-colors
              ${
                tab === key
                  ? "border-b-2 border-indigo-600 text-indigo-600"
                  : "text-gray-500 hover:text-gray-700"
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "per" && <PerSection />}
      {tab === "earnings" && <EarningsSection />}
      {tab === "report" && <ReportSection />}
    </section>
  );
}
