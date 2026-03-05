import { Loader2 } from "lucide-react";

export function LoadingRow() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-gray-400 text-sm">
      <Loader2 className="animate-spin w-4 h-4" />
      読み込み中...
    </div>
  );
}
