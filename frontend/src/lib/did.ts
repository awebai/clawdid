import bs58 from 'bs58'

const DID_KEY_PREFIX = 'did:key:z'
const MULTICODEC_ED25519 = new Uint8Array([0xed, 0x01])

export function didKeyToEd25519PublicKey(didKey: string): Uint8Array {
  if (!didKey.startsWith(DID_KEY_PREFIX)) {
    throw new Error('did:key must start with did:key:z')
  }
  const encoded = didKey.slice(DID_KEY_PREFIX.length)
  const decoded = bs58.decode(encoded)
  if (decoded.length !== 34) {
    throw new Error('did:key payload must be 34 bytes (0xed01 + 32-byte pubkey)')
  }
  if (decoded[0] !== 0xed || decoded[1] !== 0x01) {
    throw new Error('did:key multicodec prefix must be 0xed01 (Ed25519)')
  }
  return decoded.slice(2)
}

export function ed25519PublicKeyToDidKey(publicKey: Uint8Array): string {
  if (publicKey.length !== 32) {
    throw new Error('Ed25519 public key must be 32 bytes')
  }
  const payload = new Uint8Array(34)
  payload.set(MULTICODEC_ED25519, 0)
  payload.set(publicKey, 2)
  return DID_KEY_PREFIX + bs58.encode(payload)
}
