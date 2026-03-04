export function fmt(v: number | null | undefined, digits = 2): string {
  if (v == null) return "—";
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function formatPrice(value: number, name: string): string {
  if (name.includes("利回り") || name.includes("USD/JPY")) {
    return value.toLocaleString("ja-JP", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  if (value < 100) {
    return value.toLocaleString("ja-JP", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return value.toLocaleString("ja-JP", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

export function changeColor(v: number | null): string {
  if (v == null) return "text-gray-500";
  if (v > 0) return "text-green-600";
  if (v < 0) return "text-red-500";
  return "text-gray-700";
}
