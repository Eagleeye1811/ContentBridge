/** Stub for pages arriving in later phases; keeps routing and nav real from day one. */
export default function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="rounded-xl border border-dashed border-ink-200 bg-white p-10 text-center">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm text-ink-600">Arrives in {phase}.</p>
    </div>
  )
}
