import nacl from 'tweetnacl'
import { base64ToBytesRawStdNoPad, isLowerHex } from './encoding'
import { didKeyToEd25519PublicKey } from './did'
import { canonicalJsonFlatObject, sha256Hex, utf8Bytes } from './jcs'

export type DidKeyEvidence = {
  seq: number
  operation: string
  previous_did_key: string | null
  new_did_key: string
  prev_entry_hash: string | null
  entry_hash: string
  state_hash: string
  authorized_by: string
  signature: string
  timestamp: string
}

export type DidKeyResponse = {
  did_claw: string
  current_did_key: string
  log_head?: DidKeyEvidence | null
}

const LOG_ENTRY_KEYS = [
  'authorized_by',
  'did_claw',
  'new_did_key',
  'operation',
  'prev_entry_hash',
  'previous_did_key',
  'seq',
  'state_hash',
  'timestamp',
] as const

export type KeyVerificationResult =
  | {
      status: 'OK_VERIFIED'
      canonical_payload: string
      computed_entry_hash: string
    }
  | {
      status: 'OK_DEGRADED'
      reason: string
    }
  | {
      status: 'HARD_ERROR'
      reason: string
      canonical_payload?: string
      computed_entry_hash?: string
    }

export async function verifyKeyResponse(
  didClaw: string,
  body: DidKeyResponse,
  cache?: {
    cached_seq: number
    cached_entry_hash: string
  },
): Promise<KeyVerificationResult> {
  if (body.did_claw !== didClaw) {
    return { status: 'HARD_ERROR', reason: 'did_claw mismatch' }
  }

  const head = body.log_head ?? null
  if (!head) {
    return { status: 'OK_DEGRADED', reason: 'missing log_head' }
  }

  if (head.new_did_key !== body.current_did_key) {
    return { status: 'HARD_ERROR', reason: 'log_head.new_did_key != current_did_key' }
  }
  if (!Number.isInteger(head.seq) || head.seq < 1) {
    return { status: 'HARD_ERROR', reason: 'invalid seq' }
  }
  if (head.seq === 1) {
    if (head.prev_entry_hash !== null) {
      return { status: 'HARD_ERROR', reason: 'seq=1 must have prev_entry_hash=null' }
    }
    if (head.operation !== 'create') {
      return { status: 'HARD_ERROR', reason: 'seq=1 must have operation=create' }
    }
  } else {
    if (!head.prev_entry_hash || !isLowerHex(head.prev_entry_hash)) {
      return { status: 'HARD_ERROR', reason: 'seq>1 must have hex prev_entry_hash' }
    }
  }
  if (!isLowerHex(head.entry_hash) || !isLowerHex(head.state_hash)) {
    return { status: 'HARD_ERROR', reason: 'entry_hash/state_hash must be lowercase hex' }
  }

  const payloadObj: Record<string, unknown> = {
    authorized_by: head.authorized_by,
    did_claw: didClaw,
    new_did_key: head.new_did_key,
    operation: head.operation,
    prev_entry_hash: head.prev_entry_hash,
    previous_did_key: head.previous_did_key,
    seq: head.seq,
    state_hash: head.state_hash,
    timestamp: head.timestamp,
  }

  const canonical_payload = canonicalJsonFlatObject(
    payloadObj,
    [...LOG_ENTRY_KEYS] as unknown as string[],
  )
  const payloadBytes = utf8Bytes(canonical_payload)
  const computed_entry_hash = await sha256Hex(payloadBytes)
  if (computed_entry_hash !== head.entry_hash) {
    return {
      status: 'HARD_ERROR',
      reason: 'entry_hash mismatch',
      canonical_payload,
      computed_entry_hash,
    }
  }

  try {
    const pub = didKeyToEd25519PublicKey(head.authorized_by)
    const sig = base64ToBytesRawStdNoPad(head.signature)
    const ok = nacl.sign.detached.verify(payloadBytes, sig, pub)
    if (!ok) {
      return { status: 'HARD_ERROR', reason: 'signature invalid', canonical_payload }
    }
  } catch (e) {
    return {
      status: 'HARD_ERROR',
      reason: `signature verification error: ${(e as Error).message}`,
      canonical_payload,
    }
  }

  if (cache) {
    if (head.seq < cache.cached_seq) {
      return { status: 'HARD_ERROR', reason: 'regression: seq decreased', canonical_payload }
    }
    if (head.seq === cache.cached_seq && head.entry_hash !== cache.cached_entry_hash) {
      return { status: 'HARD_ERROR', reason: 'split view: same seq, different entry_hash', canonical_payload }
    }
    if (head.seq > cache.cached_seq && head.prev_entry_hash !== cache.cached_entry_hash) {
      return { status: 'HARD_ERROR', reason: 'broken chain: prev_entry_hash != cached entry_hash', canonical_payload }
    }
  }

  return { status: 'OK_VERIFIED', canonical_payload, computed_entry_hash }
}

export type DidLogEntry = {
  did_claw: string
  seq: number
  operation: string
  previous_did_key: string | null
  new_did_key: string
  prev_entry_hash: string | null
  entry_hash: string
  state_hash: string
  authorized_by: string
  signature: string
  timestamp: string
}

export async function verifyLogEntries(entries: DidLogEntry[]): Promise<{
  ok: boolean
  errors: string[]
}> {
  const errors: string[] = []
  let prevEntryHash: string | null = null

  for (const e of entries) {
    const payloadObj: Record<string, unknown> = {
      authorized_by: e.authorized_by,
      did_claw: e.did_claw,
      new_did_key: e.new_did_key,
      operation: e.operation,
      prev_entry_hash: e.prev_entry_hash,
      previous_did_key: e.previous_did_key,
      seq: e.seq,
      state_hash: e.state_hash,
      timestamp: e.timestamp,
    }
    const canonical = canonicalJsonFlatObject(payloadObj, [...LOG_ENTRY_KEYS] as unknown as string[])
    const bytes = utf8Bytes(canonical)
    const h = await sha256Hex(bytes)
    if (h !== e.entry_hash) errors.push(`seq ${e.seq}: entry_hash mismatch`)

    if (e.seq === 1) {
      if (e.prev_entry_hash !== null) errors.push('seq 1: prev_entry_hash must be null')
    } else {
      if (prevEntryHash && e.prev_entry_hash !== prevEntryHash) {
        errors.push(`seq ${e.seq}: prev_entry_hash mismatch`)
      }
    }

    try {
      const pub = didKeyToEd25519PublicKey(e.authorized_by)
      const sig = base64ToBytesRawStdNoPad(e.signature)
      const ok = nacl.sign.detached.verify(bytes, sig, pub)
      if (!ok) errors.push(`seq ${e.seq}: signature invalid`)
    } catch (err) {
      errors.push(`seq ${e.seq}: signature verify error: ${(err as Error).message}`)
    }

    prevEntryHash = e.entry_hash
  }

  return { ok: errors.length === 0, errors }
}

