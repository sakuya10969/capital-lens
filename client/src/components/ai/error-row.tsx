import { RefreshCw } from "lucide-react";

export function ErrorRow({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center space-y-3">
      <p className="text-red-600 text-sm">データの取得に失敗しました。</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium
                   bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        再試行
      </button>
    </div>
  );
}
