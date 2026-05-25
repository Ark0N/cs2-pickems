export function Bar({ value, color = "#4f9dde" }: { value: number; color?: string }) {
  return (
    <div className="bar-track">
      <div className="bar-fill" style={{ width: `${Math.round(value * 100)}%`, background: color }} />
      <span className="bar-label">{(value * 100).toFixed(1)}%</span>
    </div>
  );
}
