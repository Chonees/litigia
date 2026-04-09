/**
 * Litigia Sovereign — Shared UI Primitives
 *
 * Reusable components following the Sovereign design system.
 * 0px border-radius, bottom-border inputs, gold accents.
 */

import type { ReactNode } from "react";

/* ─── Section Header ────────────────────────────────────────────── */

export function SectionHeader({
  label,
  title,
}: {
  label: string;
  title: string;
}) {
  return (
    <div className="mb-6 animate-slide-down">
      <span className="text-[11px] font-semibold tracking-[0.2em] uppercase text-[var(--primary-container)]">
        {label}
      </span>
      <h2 className="font-heading text-3xl font-bold text-[var(--on-surface)] mt-1 tracking-tight">
        {title}
      </h2>
      <div className="mt-3 h-[1px] gold-gradient animate-line-grow" style={{ maxWidth: "4rem" }} />
    </div>
  );
}

/* ─── Card ──────────────────────────────────────────────────────── */

export function Card({
  children,
  className = "",
  accent,
}: {
  children: ReactNode;
  className?: string;
  accent?: "gold" | "danger";
}) {
  const border = accent === "danger"
    ? "border-l-2 border-l-[var(--danger)]"
    : accent === "gold"
    ? "border-l-2 border-l-[var(--primary)]"
    : "";

  return (
    <div className={`bg-[var(--container-high)] p-5 transition-all duration-300 hover:shadow-sm ${border} ${className}`}>
      {children}
    </div>
  );
}

/* ─── Card Header ───────────────────────────────────────────────── */

export function CardHeader({
  children,
  variant = "gold",
}: {
  children: ReactNode;
  variant?: "gold" | "danger" | "muted";
}) {
  const color = variant === "danger"
    ? "text-[var(--danger)]"
    : variant === "muted"
    ? "text-[var(--muted)]"
    : "text-[var(--primary)]";

  return (
    <h4 className={`text-[11px] font-semibold tracking-[0.15em] uppercase ${color} mb-3`}>
      {children}
    </h4>
  );
}

/* ─── Label ─────────────────────────────────────────────────────── */

export function Label({ children }: { children: ReactNode }) {
  return (
    <label className="block text-[11px] font-semibold tracking-[0.1em] uppercase text-[var(--primary-container)] mb-2">
      {children}
    </label>
  );
}

/* ─── Input ─────────────────────────────────────────────────────── */

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full px-0 py-3 text-sm bg-transparent ${props.className ?? ""}`}
    />
  );
}

/* ─── Select ────────────────────────────────────────────────────── */

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <select
      {...props}
      className={`w-full px-0 py-3 text-sm bg-transparent cursor-pointer ${props.className ?? ""}`}
    >
      {props.children}
    </select>
  );
}

/* ─── Textarea ──────────────────────────────────────────────────── */

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full px-0 py-3 text-sm bg-transparent resize-none ${props.className ?? ""}`}
    />
  );
}

/* ─── Primary Button ────────────────────────────────────────────── */

export function GoldButton({
  children,
  disabled,
  type = "submit",
}: {
  children: ReactNode;
  disabled?: boolean;
  type?: "submit" | "button";
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className="w-full py-3.5 gold-gradient text-[var(--on-primary)] font-semibold text-sm tracking-wide uppercase transition-all duration-500 hover:shadow-[0_4px_24px_rgba(154,123,45,0.2)] hover:translate-y-[-1px] active:translate-y-[1px] active:shadow-none disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-none"
    >
      {children}
    </button>
  );
}

/* ─── Chip / Tag ────────────────────────────────────────────────── */

export function Chip({
  children,
  variant = "gold",
}: {
  children: ReactNode;
  variant?: "gold" | "danger" | "muted";
}) {
  const styles = {
    gold: "border-l-2 border-l-[var(--primary)] bg-[var(--container)] text-[var(--primary)]",
    danger: "border-l-2 border-l-[var(--danger)] bg-[var(--danger-container)]/10 text-[var(--danger)]",
    muted: "border-l-2 border-l-[var(--outline-variant)] bg-[var(--container)] text-[var(--muted)]",
  };

  return (
    <span className={`inline-block px-3 py-1 text-[11px] tracking-wide uppercase font-medium ${styles[variant]}`}>
      {children}
    </span>
  );
}

/* ─── Stat Box ──────────────────────────────────────────────────── */

export function StatBox({
  value,
  label,
  variant = "gold",
  large,
}: {
  value: string | number;
  label: string;
  variant?: "gold" | "danger" | "muted";
  large?: boolean;
}) {
  const color = variant === "danger"
    ? "text-[var(--danger)]"
    : variant === "muted"
    ? "text-[var(--muted)]"
    : "text-[var(--primary)]";

  return (
    <div className="bg-[var(--container)] p-4 text-center">
      <div className={`${large ? "text-3xl" : "text-xl"} font-bold font-heading ${color}`}>
        {value}
      </div>
      <div className="text-[10px] tracking-[0.1em] uppercase text-[var(--muted)] mt-1">
        {label}
      </div>
    </div>
  );
}
