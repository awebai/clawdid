export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    let detail = ''
    try {
      const parsed = JSON.parse(text) as unknown
      if (
        parsed &&
        typeof parsed === 'object' &&
        'detail' in parsed &&
        typeof (parsed as { detail?: unknown }).detail === 'string'
      ) {
        detail = (parsed as { detail: string }).detail
      }
    } catch {
      // ignore
    }
    const msg = detail || text
    throw new Error(`${res.status} ${res.statusText}${msg ? `: ${msg}` : ''}`)
  }
  return (await res.json()) as T
}
