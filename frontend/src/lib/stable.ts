import bs58 from 'bs58'
import { didKeyToEd25519PublicKey } from './did'

export async function didKeyToStableId(
  didKey: string,
  method: 'claw' | 'aw' = 'claw',
): Promise<string> {
  const publicKey = didKeyToEd25519PublicKey(didKey)
  const digest = await crypto.subtle.digest('SHA-256', publicKey)
  const bytes = new Uint8Array(digest).slice(0, 20)
  const suffix = bs58.encode(bytes)
  return method === 'claw' ? `did:claw:${suffix}` : `did:aw:${suffix}`
}

