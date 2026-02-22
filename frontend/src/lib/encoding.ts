export function base64ToBytesRawStdNoPad(b64NoPad: string): Uint8Array {
  const padLen = (4 - (b64NoPad.length % 4)) % 4
  const padded = b64NoPad + '='.repeat(padLen)
  const bin = atob(padded)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

export function bytesToHex(bytes: Uint8Array): string {
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export function isLowerHex(s: string): boolean {
  return /^[0-9a-f]+$/.test(s)
}

