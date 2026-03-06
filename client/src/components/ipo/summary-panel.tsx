import { ExternalLink, Loader2, RefreshCw } from "lucide-react";

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
        <button
          onClick={() => onRetry(code)}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium
                     text-red-600 bg-red-100 hover:bg-red-200 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          再試行
        </button>
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
      <ul className="space-y-1">
        {data.bullets.map((bullet, i) => (
          <li key={i} className="flex gap-2 text-sm text-gray-700">
            <span className="text-blue-400 mt-0.5 shrink-0">・</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
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
