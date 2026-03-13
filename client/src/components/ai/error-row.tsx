import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorRow({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center space-y-3">
      <p className="text-red-600 text-sm">データの取得に失敗しました。</p>
      <Button
        onClick={onRetry}
        variant="ghost"
        size="sm"
        className="h-auto bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 hover:text-red-700"
      >
        <RefreshCw className="w-3 h-3" />
        再試行
      </Button>
    </div>
  );
}
