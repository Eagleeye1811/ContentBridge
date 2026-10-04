/** Small shared building blocks, so every page looks and behaves the same. */
import type { ReactNode } from 'react'
import { TONE_CLASS } from '@/lib/labels'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-ink-200 bg-white p-5 shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  icon,
  action,
}: {
  title: string
  subtitle?: string
  icon?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start gap-4">
      {icon && (
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-brand-600">
          {icon}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-ink-600">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function Badge({
  tone,
  children,
}: {
  tone: keyof typeof TONE_CLASS
  children: ReactNode
}) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE_CLASS[tone]}`}>
      {children}
    </span>
  )
}

export function Button({
  children,
  onClick,
  disabled,
  variant = 'primary',
  size = 'md',
  type = 'button',
  title,
  wide = false,
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md'
  type?: 'button' | 'submit'
  title?: string
  wide?: boolean
  className?: string
}) {
  const look = {
    primary: 'bg-brand-600 text-white hover:bg-brand-500',
    secondary: 'bg-white text-ink-900 ring-1 ring-ink-200 hover:ring-ink-400',
    danger: 'bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50',
    ghost: 'text-ink-600 hover:bg-ink-100 hover:text-ink-900',
  }[variant]
  const pad = size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm'
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${look} ${pad} ${wide ? 'w-full' : ''} ${className}`}
    >
      {children}
    </button>
  )
}

export function Notice({
  tone = 'info',
  children,
}: {
  tone?: 'info' | 'warn' | 'bad' | 'good'
  children: ReactNode
}) {
  const look = {
    info: 'bg-blue-50 text-blue-900',
    warn: 'bg-amber-50 text-amber-900',
    bad: 'bg-red-50 text-red-800',
    good: 'bg-emerald-50 text-emerald-900',
  }[tone]
  return <div className={`rounded-xl px-4 py-3 text-sm ${look}`}>{children}</div>
}

export function Empty({
  title,
  children,
  icon,
}: {
  title: string
  children?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-dashed border-ink-200 bg-white px-6 py-12 text-center">
      {icon && (
        <span className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-ink-100 text-ink-400">
          {icon}
        </span>
      )}
      <p className="text-sm font-medium">{title}</p>
      {children && <div className="mx-auto mt-1 max-w-md text-sm text-ink-600">{children}</div>}
    </div>
  )
}

export function Progress({ value, label }: { value: number; label?: string }) {
  return (
    <div>
      <div className="h-1.5 overflow-hidden rounded-full bg-ink-200">
        <div
          className="h-full rounded-full bg-brand-600 transition-all duration-300"
          style={{ width: `${Math.max(value * 100, 4)}%` }}
        />
      </div>
      {label && <p className="mt-1.5 text-xs text-ink-600">{label}</p>}
    </div>
  )
}

/** Single choice shown as buttons, for short option lists. */
export function Segmented({
  options,
  value,
  onChange,
  className = '',
}: {
  options: { key: string; label: string }[]
  value: string
  onChange: (key: string) => void
  className?: string
}) {
  return (
    <div className={`inline-flex flex-wrap gap-1 rounded-xl bg-ink-100/90 p-1 border border-ink-200/60 ${className}`}>
      {options.map((o) => {
        const active = o.key === value
        return (
          <button
            key={o.key}
            type="button"
            onClick={() => onChange(o.key)}
            aria-pressed={active}
            className={`rounded-lg px-3 py-1.5 text-xs sm:text-sm font-medium transition-all ${
              active
                ? 'bg-white text-ink-950 shadow-sm ring-1 ring-black/5 font-semibold'
                : 'text-ink-600 hover:text-ink-900 hover:bg-white/50'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

export function Select({
  value,
  onChange,
  options,
  className = '',
}: {
  value: string
  onChange: (key: string) => void
  options: { key: string; label: string }[]
  className?: string
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full appearance-none rounded-xl border border-ink-200 bg-white px-3.5 py-2.5 pr-9 text-sm text-ink-900 shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 ${className}`}
      >
        {options.map((o) => (
          <option key={o.key} value={o.key}>
            {o.label}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-ink-400">
        <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
        </svg>
      </div>
    </div>
  )
}

export function Field({
  label,
  help,
  children,
  className = '',
}: {
  label: string
  help?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-700">{label}</p>
        {help && <p className="text-xs text-ink-400">{help}</p>}
      </div>
      <div>{children}</div>
    </div>
  )
}

