import { MarketOverview } from "@/components/market-overview";
import { IpoTable } from "@/components/ipo-table";
import type { MarketOverviewResponse } from "@/types/market";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchMarketOverview(): Promise<MarketOverviewResponse | null> {
  try {
    const res = await fetch(`${API_URL}/api/market/overview`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function Home() {
  const market = await fetchMarketOverview();

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-10">
        {market ? (
          <MarketOverview data={market} />
        ) : (
          <ErrorCard title="資本市場ダッシュボード" />
        )}

        {/* IpoTable はクライアントコンポーネント: 一覧フェッチ・エラー・retry・オンデマンド要約をすべて内包 */}
        <IpoTable />
      </div>
    </main>
  );
}

function ErrorCard({ title }: { title: string }) {
  return (
    <section>
      <h1 className="text-xl font-bold text-gray-900 mb-4">{title}</h1>
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center text-red-600 text-sm">
        データの取得に失敗しました。バックエンドサーバーが起動しているか確認してください。
      </div>
    </section>
  );
}
