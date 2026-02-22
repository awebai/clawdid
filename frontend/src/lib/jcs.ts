export function canonicalJsonFlatObject(
  obj: Record<string, unknown>,
  orderedKeys: string[],
): string {
  // For flat objects only. Uses JSON.stringify with an explicit key order.
  // This is sufficient for ClaWDID log entry payloads (no nested objects/arrays).
  return JSON.stringify(obj, orderedKeys)
}

export function utf8Bytes(s: string): Uint8Array {
  return new TextEncoder().encode(s)
}

export async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

