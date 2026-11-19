import type { ReactNode } from "react";

const ICONS = {
  left: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </>
  ),
};

type Props = { icon: keyof typeof ICONS; title: string; hint?: string; children?: ReactNode };

export function StatusCard({ icon, title, hint, children }: Props) {
  return (
    <section className="card status-card stage-enter">
      <div className="status-mark" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {ICONS[icon]}
        </svg>
      </div>
      <h1 className="status-title">{title}</h1>
      {hint && <p className="status-hint">{hint}</p>}
      {children && <div className="status-actions">{children}</div>}
    </section>
  );
}
