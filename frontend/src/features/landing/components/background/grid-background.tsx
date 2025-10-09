export function GridBackground({ className = '' }: { className?: string }) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 ${className}`}
      style={{
        backgroundImage: `
          linear-gradient(rgba(45,45,37,0.03) 1px, transparent 2px),
          linear-gradient(90deg, rgba(45,45,37,0.03) 1px, transparent 2px)
        `,
        backgroundSize: 'min(80px, 12vw) min(80px, 12vw)',
      }}
    />
  );
}
