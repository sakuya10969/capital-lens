import { ExternalLink, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { LoadState } from "@/types/common";
import type { IpoSummaryResponse } from "@/types/ipo";

export function SummaryPanel({
  code,
  companyUrl,
  outlinePdfUrl,
  state,
  onRetry,
}: {
  code: string;
  companyUrl?: string | null;
  outlinePdfUrl?: string | null;
  state: LoadState<IpoSummaryResponse>;
  onRetry: (code: string) => void;
}) {
  if (state.status === "idle" || state.status === "loading") {
    return (
      <div className="flex items-center gap-2 text-gray-400 text-sm">
        <Loader2 className="animate-spin w-4 h-4" />
        会社概要を読み込み中...
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="text-red-500">会社概要の取得に失敗しました。</span>
        <Button
          onClick={() => onRetry(code)}
          variant="ghost"
          size="sm"
          className="h-auto bg-red-100 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-200 hover:text-red-600"
        >
          <RefreshCw className="w-3 h-3" />
          再試行
        </Button>
      </div>
    );
  }

  const { data } = state;
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-blue-700">会社概要</span>
        {data.cached && (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            キャッシュ
          </span>
        )}
      </div>
      <div className="mb-2 space-y-1">
        {companyUrl && (
          <a
            href={companyUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            <ExternalLink className="w-4 h-4" />
            JPX企業ページ
          </a>
        )}
      </div>
      <p className="text-sm text-gray-700 leading-relaxed">{data.summary}</p>
      <div className="mt-1 space-y-1">
        {outlinePdfUrl && (
              <a
                href={outlinePdfUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 hover:underline"
              >
                <ExternalLink className="w-4 h-4" />
                会社概要の参照元（PDF）
              </a>
            )}
        </div>
    </div>
  );
}
