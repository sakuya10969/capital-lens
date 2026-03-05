import { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";

import { generateAiConsultingReport } from "@/lib/api/ai-consulting";
import type { LoadState } from "@/types/common";
import type { ReportResponse } from "@/types/ai_consulting";

export function ReportSection() {
  const [state, setState] = useState<LoadState<ReportResponse>>({
    status: "idle",
  });

  const generate = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const data = await generateAiConsultingReport();
      setState({ status: "done", data });
    } catch {
      setState({ status: "error" });
    }
  }, []);

  return (
    <div className="space-y-4">
      <button
        onClick={generate}
        disabled={state.status === "loading"}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium
                   hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {state.status === "loading" && (
          <Loader2 className="animate-spin w-4 h-4" />
        )}
        レポートを生成
      </button>

      {state.status === "error" && (
        <p className="text-sm text-red-500">
          レポートの生成に失敗しました。再度お試しください。
        </p>
      )}

      {state.status === "done" && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed">
              {state.data.text_report}
            </pre>
          </div>
          <details className="rounded-lg border border-gray-200">
            <summary className="px-4 py-2 text-sm text-gray-500 cursor-pointer select-none hover:bg-gray-50">
              生データを見る (JSON)
            </summary>
            <pre className="px-4 py-3 text-xs text-gray-600 overflow-auto max-h-96 whitespace-pre-wrap">
              {JSON.stringify(
                { per: state.data.per, earnings: state.data.earnings },
                null,
                2,
              )}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
