type CloudVariant = 'beige' | 'orange' | 'dark' | 'light';

interface CloudShapeThreeProps {
  className?: string;
  variant?: CloudVariant;
}

export function CloudShapeThree({ className = '', variant = 'beige' }: CloudShapeThreeProps) {
  const variantStyles: Record<CloudVariant, Record<string, string>> = {
    beige: {
      background:
        'radial-gradient(ellipse at 80% 20%, var(--primary-beige) 0%, rgba(251,243,228,0.5) 50%, transparent 85%)',
    },
    orange: {
      background:
        'radial-gradient(ellipse at 30% 80%, rgba(221,97,50,0.4) 0%, rgba(221,97,50,0.15) 60%, transparent 90%)',
    },
    dark: {
      background:
        'radial-gradient(ellipse at 60% 40%, rgba(45,45,37,0.15) 0%, rgba(45,45,37,0.05) 70%, transparent 100%)',
    },
    light: {
      background:
        'radial-gradient(ellipse at 40% 60%, rgba(255,255,255,0.6) 0%, rgba(255,255,255,0.2) 60%, transparent 95%)',
    },
  };

  return (
    <div
      className={`pointer-events-none absolute ${className}`}
      style={{
        width: 'clamp(220px, 45vw, 520px)',
        height: 'clamp(160px, 35vw, 380px)',
        ...variantStyles[variant],
        clipPath:
          'polygon(20% 0%, 80% 5%, 100% 25%, 95% 50%, 85% 75%, 60% 95%, 30% 100%, 8% 90%, 0% 65%, 5% 40%, 12% 18%)',
        filter: 'blur(3px)',
        transform: 'rotate(-60deg)',
      }}
    />
  );
}
