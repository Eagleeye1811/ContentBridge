/** Output types in the order they appear in menus, grouped for the navbar. */
export const FORMAT_GROUPS: { label: string; keys: string[] }[] = [
  { label: 'Documents', keys: ['advisory', 'summary', 'report', 'email', 'press_release'] },
  { label: 'Presentation & media', keys: ['ppt', 'linkedin', 'twitter', 'infographic', 'video'] },
]

export const FORMAT_KEYS = FORMAT_GROUPS.flatMap((g) => g.keys)

/** Outputs stored before the LinkedIn rename still belong to its page. */
export const typeOf = (o: { type: string }) => (o.type === 'social' ? 'linkedin' : o.type)

/** Newest version of each piece of content; older versions are history. */
export function latestOnly<
  T extends { document_id: string; type: string; audience: string; language: string; version: number; created_at: string },
>(outputs: T[]): T[] {
  const seen = new Map<string, T>()
  for (const o of outputs) {
    const key = `${o.document_id}|${typeOf(o)}|${o.audience}|${o.language}`
    const prev = seen.get(key)
    if (!prev || o.version > prev.version) seen.set(key, o)
  }
  return [...seen.values()].sort((a, b) => b.created_at.localeCompare(a.created_at))
}
