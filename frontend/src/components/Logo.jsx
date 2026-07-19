/**
 * AutoSage mark — a steering wheel. Draws in `currentColor`, so it inherits the
 * accent color wherever it's placed (deep blue on light, bright blue on dark).
 */
export default function Logo({ size = 24, ...props }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      role="img"
      aria-label="AutoSage"
      {...props}
    >
      <circle cx="50" cy="50" r="38" stroke="currentColor" strokeWidth="9" />
      <circle cx="50" cy="50" r="12" fill="currentColor" />
      {/* three spokes */}
      <path d="M50 62 V86" stroke="currentColor" strokeWidth="9" strokeLinecap="round" />
      <path d="M39.6 56 L18 69" stroke="currentColor" strokeWidth="9" strokeLinecap="round" />
      <path d="M60.4 56 L82 69" stroke="currentColor" strokeWidth="9" strokeLinecap="round" />
    </svg>
  );
}
