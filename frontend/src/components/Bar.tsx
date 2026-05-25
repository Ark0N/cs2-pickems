export type BarVariant = "accent" | "advance" | "three" | "zero" | "champion";

export function Bar({ value, variant = "accent" }: { value: number; variant?: BarVariant }) {
  return (
    <div className="bar-track">
      <div
        className={`bar-fill bar-${variant}`}
        style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
      />
      <span className="bar-label">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}
