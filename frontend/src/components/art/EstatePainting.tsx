import styles from "./estate.module.css";

export function EstatePainting({ className }: { className?: string }) {
  return (
    <svg className={`${styles.painting} ${className ?? ""}`} viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9ec8ba" />
          <stop offset="100%" stopColor="#f4efe4" />
        </linearGradient>
      </defs>
      <rect width="1200" height="600" fill="url(#sky)" />
      <path d="M0 380 C200 280 400 420 600 300 C800 180 1000 360 1200 260 V600 H0 Z" fill="#6ea384" />
      <path d="M0 460 C250 380 450 520 700 400 C950 300 1100 480 1200 420 V600 H0 Z" fill="#3f7a56" />
      <circle cx="180" cy="120" r="48" fill="#fff6e4" />
    </svg>
  );
}
