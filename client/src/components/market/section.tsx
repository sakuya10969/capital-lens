import type { MarketItem } from "@/types/market";

import { MarketCard } from "@/components/market/market-card";

export function Section({
  title,
  items,
}: {
  title: string;
  items: MarketItem[];
}) {
  if (items.length === 0) return null;
  return (
    <div>
      <h2 className="text-base font-semibold text-black mb-3">{title}</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {items.map((item) => (
          <MarketCard key={item.name} item={item} />
        ))}
      </div>
    </div>
  );
}
