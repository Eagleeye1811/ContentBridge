/** Minimal server-sent-events framing, kept pure so it can be tested directly. */

export interface SseEvent {
  event: string
  data: string
}

/**
 * Split whatever has accumulated in `buffer` into complete SSE frames.
 * Returns the parsed events plus the trailing partial frame to carry forward.
 */
export function parseSseFrames(buffer: string): { events: SseEvent[]; rest: string } {
  // Frames are separated by a blank line; tolerate CRLF from proxies.
  const normalized = buffer.replace(/\r\n/g, '\n')
  const chunks = normalized.split('\n\n')
  const rest = chunks.pop() ?? ''
  const events: SseEvent[] = []

  for (const chunk of chunks) {
    let event = 'message'
    const data: string[] = []
    for (const line of chunk.split('\n')) {
      if (line.startsWith(':')) continue // comment / keep-alive
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) data.push(line.slice(5).trim())
    }
    if (data.length) events.push({ event, data: data.join('\n') })
  }

  return { events, rest }
}
