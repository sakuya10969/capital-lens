import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatPrice } from "@/lib/formatters";
import type { MarketItem } from "@/types/market";

import { ChangeIndicator } from "@/components/market/change-indicator";

export function MarketCard({ item }: { item: MarketItem }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{item.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold text-gray-900 mb-1">
          {formatPrice(item.current_price, item.name)}
        </p>
        <ChangeIndicator
          change={item.change}
          changePercent={item.change_percent}
        />
      </CardContent>
    </Card>
  );
}
