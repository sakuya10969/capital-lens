export function Note({ text }: { text: string | null }) {
  if (!text) return null;
  return <span className="block text-xs text-gray-400 mt-0.5">{text}</span>;
}
