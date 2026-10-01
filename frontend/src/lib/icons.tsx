/** A small inline icon set, so the app needs no icon library. */
const PATHS: Record<string, string> = {
  // formats
  advisory: 'M12 3l8 4v5c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V7l8-4zM12 8v4M12 15.5h.01',
  ppt: 'M3 4h18v12H3zM8 20h8M12 16v4M7 12l3-3 2 2 4-4',
  summary: 'M6 3h9l5 5v13H6zM14 3v6h6M9 13h8M9 17h5',
  email: 'M3 6h18v12H3zM3 7l9 6 9-6',
  linkedin: 'M4 4h16v16H4zM8 10v6M8 7.5h.01M12 16v-6M12 13a2 2 0 0 1 4 0v3',
  press_release: 'M5 4h12v16H5a2 2 0 0 1-2-2V8h2M17 8h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2M8 8h6M8 12h6M8 16h4',
  report: 'M6 3h12v18H6zM9 15v2M12 11v6M15 13v4M9 7h6',
  infographic: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  video: 'M3 6h13v12H3zM16 10l5-3v10l-5-3',
  // navigation
  document: 'M6 3h9l5 5v13H6zM14 3v6h6',
  facts: 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01',
  check: 'M9 12l2 2 4-4M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
  sources: 'M4 5h6l2 2h8v12H4z',
  approvals: 'M20 6L9 17l-5-5',
  plus: 'M12 5v14M5 12h14',
  back: 'M15 18l-6-6 6-6',
  trash: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13',
  download: 'M12 4v11M7 10l5 5 5-5M5 20h14',
  edit: 'M4 20h4L19 9l-4-4L4 16v4z',
  upload: 'M12 20V9M7 14l5-5 5 5M5 4h14',
  image: 'M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M15 9h.01',
  text: 'M5 6h14M5 10h14M5 14h10M5 18h7',
  logout: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10',
  spark: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
}

export function Icon({
  name,
  className = 'h-4 w-4',
}: {
  name: string
  className?: string
}) {
  const d = PATHS[name] ?? PATHS.document
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  )
}
