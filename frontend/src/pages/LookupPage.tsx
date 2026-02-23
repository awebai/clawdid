import { useMemo, useState } from 'react'
import CopyableValue from '../components/CopyableValue'
import { apiBaseUrl } from '../lib/config'
import { fetchJson } from '../lib/http'
import { verifyKeyResponse, type DidKeyResponse } from '../lib/clawdid'
import { didKeyToEd25519PublicKey, ed25519PublicKeyToDidKey } from '../lib/did'
import { isStableId } from '../lib/stable'
import { bytesToBase64RawStdNoPad } from '../lib/encoding'
import nacl from 'tweetnacl'
import { canonicalJsonFlatObject, sha256Hex, utf8Bytes } from '../lib/jcs'

type CacheEntry = { seq: number; entry_hash: string }

function cacheKey(didClaw: string) {
  return `clawdid_key_cache:${didClaw}`
}

function loadCache(didClaw: string): CacheEntry | null {
  try {
    const raw = localStorage.getItem(cacheKey(didClaw))
    if (!raw) return null
    const data = JSON.parse(raw) as CacheEntry
    if (!Number.isInteger(data.seq) || typeof data.entry_hash !== 'string') return null
    return data
  } catch {
    return null
  }
}

function saveCache(didClaw: string, entry: CacheEntry) {
  try {
    localStorage.setItem(cacheKey(didClaw), JSON.stringify(entry))
  } catch {
    // ignore
  }
}

function StatusPill({ status }: { status: string }) {
  const cls =
    status === 'OK_VERIFIED'
      ? 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/30'
      : status === 'OK_DEGRADED'
        ? 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/30'
        : 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${cls}`}>
      {status}
    </span>
  )
}

type DidFullResponse = {
  did_claw: string
  current_did_key: string
  server: string
  address: string
  handle: string | null
  created_at: string
  updated_at: string
}

const STATE_KEYS = ['address', 'current_did_key', 'did_claw', 'handle', 'server'] as const

function nowRfc3339SecondsZ(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
}

export default function LookupPage() {
  const apiBase = useMemo(() => apiBaseUrl(), [])
  const [didClaw, setDidClaw] = useState('')
  const [observedDidKey, setObservedDidKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resp, setResp] = useState<DidKeyResponse | null>(null)
  const [verification, setVerification] = useState<
    Awaited<ReturnType<typeof verifyKeyResponse>> | null
  >(null)
  const [crossCheckError, setCrossCheckError] = useState<string | null>(null)
  const [fullLoading, setFullLoading] = useState(false)
  const [fullError, setFullError] = useState<string | null>(null)
  const [fullResp, setFullResp] = useState<DidFullResponse | null>(null)
  const [stateHash, setStateHash] = useState<string | null>(null)
  const [stateHashStatus, setStateHashStatus] = useState<'PASS' | 'FAIL' | 'DEGRADED' | null>(
    null,
  )
  const didInputId = 'did-claw'
  const didKeyInputId = 'did-key'

  async function fetchFull(id: string) {
    setFullError(null)
    setFullResp(null)
    setStateHash(null)
    setStateHashStatus(null)

    setFullLoading(true)
    try {
      const keypair = nacl.sign.keyPair()
      const authDidKey = ed25519PublicKeyToDidKey(keypair.publicKey)

      const ts = nowRfc3339SecondsZ()
      const path = `/v1/did/${encodeURIComponent(id)}/full`
      const signingPayload = utf8Bytes(`${ts}\nGET\n${path}`)
      const sigBytes = nacl.sign.detached(signingPayload, keypair.secretKey)
      const sigB64 = bytesToBase64RawStdNoPad(sigBytes)

      const body = await fetchJson<DidFullResponse>(`${apiBase}${path}`, {
        headers: {
          Authorization: `DIDKey ${authDidKey} ${sigB64}`,
          'X-ClawDID-Timestamp': ts,
        },
      })
      setFullResp(body)

      const stateObj: Record<string, unknown> = {
        address: body.address,
        current_did_key: body.current_did_key,
        did_claw: body.did_claw,
        handle: body.handle,
        server: body.server,
      }
      const canonical = canonicalJsonFlatObject(stateObj, [...STATE_KEYS] as unknown as string[])
      const computed = await sha256Hex(utf8Bytes(canonical))
      setStateHash(computed)

      const head = resp?.log_head ?? null
      if (!head) {
        setStateHashStatus('DEGRADED')
        return
      }
      if (computed !== head.state_hash) {
        setStateHashStatus('FAIL')
        return
      }
      setStateHashStatus('PASS')
    } catch (e) {
      setFullError((e as Error).message)
    } finally {
      setFullLoading(false)
    }
  }

  async function onLookup() {
    const id = didClaw.trim()
    const observed = observedDidKey.trim()
    setError(null)
    setResp(null)
    setVerification(null)
    setCrossCheckError(null)
    setFullError(null)
    setFullResp(null)
    setStateHash(null)
    setStateHashStatus(null)
    if (!id) return
    if (!isStableId(id)) {
      setError('Stable ID must start with did:claw: or did:aw:.')
      return
    }
    if (observed) {
      try {
        didKeyToEd25519PublicKey(observed)
      } catch (e) {
        setError(`Observed did:key is invalid: ${(e as Error).message}`)
        return
      }
    }
    setLoading(true)
    try {
      const body = await fetchJson<DidKeyResponse>(`${apiBase}/did/${encodeURIComponent(id)}/key`)
      setResp(body)
      const cached = loadCache(id)
      const vr = await verifyKeyResponse(
        id,
        body,
        cached ? { cached_seq: cached.seq, cached_entry_hash: cached.entry_hash } : undefined,
      )
      setVerification(vr)
      if (vr.status === 'OK_VERIFIED' && body.log_head) {
        saveCache(id, { seq: body.log_head.seq, entry_hash: body.log_head.entry_hash })
      }
      if (observed) {
        if (observed !== body.current_did_key) {
          setCrossCheckError(
            [
              'Split-trust cross-check failed:',
              'observed did:key does not match ClawDID current_did_key.',
              'Treat this as security-relevant (server compromise, stale data, or rotation in flight).',
            ].join(' '),
          )
        }
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
        <h1 className="text-lg font-semibold text-white">Lookup stable identity</h1>
        <p className="mt-1 text-sm text-slate-400">
          Fetches <code className="rounded bg-slate-900 px-1">/did/&lt;did:claw&gt;/key</code>, verifies the
          returned <code className="rounded bg-slate-900 px-1">log_head</code> locally, and (optionally)
          cross-checks an observed <code className="rounded bg-slate-900 px-1">did:key</code>.
        </p>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <div className="w-full sm:flex-1">
            <label htmlFor={didInputId} className="mb-1 block text-xs text-slate-500">
              Stable ID
            </label>
            <input
              id={didInputId}
              value={didClaw}
              onChange={(e) => setDidClaw(e.target.value)}
              placeholder="did:claw:..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter') void onLookup()
              }}
            />
          </div>
          <div className="w-full sm:flex-1">
            <label htmlFor={didKeyInputId} className="mb-1 block text-xs text-slate-500">
              Observed did:key (optional)
            </label>
            <input
              id={didKeyInputId}
              value={observedDidKey}
              onChange={(e) => setObservedDidKey(e.target.value)}
              placeholder="did:key:z..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter') void onLookup()
              }}
            />
          </div>
          <button
            onClick={onLookup}
            disabled={loading}
            className="rounded-xl bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-60"
          >
            {loading ? 'Looking…' : 'Lookup'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {error}
          </div>
        )}
        {crossCheckError && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {crossCheckError}
          </div>
        )}
      </div>

      {(resp || verification) && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Result</h2>
              {verification && <StatusPill status={verification.status} />}
            </div>
            {resp && (
              <div className="mt-3 space-y-2 text-sm">
                <CopyableValue label="did_claw" value={resp.did_claw} />
                <CopyableValue label="current_did_key" value={resp.current_did_key} />
                {observedDidKey.trim() ? (
                  <CopyableValue label="observed_did_key" value={observedDidKey.trim()} />
                ) : null}
              </div>
            )}
            {verification?.status !== 'OK_VERIFIED' && verification && (
              <div className="mt-4 text-sm text-slate-300">
                <div className="text-xs text-slate-500">Reason</div>
                <div className="break-words">{(verification as any).reason}</div>
              </div>
            )}
            {verification?.status === 'OK_VERIFIED' && (
              <div className="mt-4 text-sm text-emerald-200">
                Verified log head signature + entry_hash.
              </div>
            )}
            {verification?.status === 'OK_VERIFIED' && observedDidKey.trim() && !crossCheckError && resp && (
              <div className="mt-2 text-sm text-emerald-200">
                Split-trust cross-check: observed did:key matches.
              </div>
            )}

            <div className="mt-5 border-t border-slate-800/70 pt-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-white">Mapping details</div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    Fetches <code className="rounded bg-slate-900 px-1">/did/&lt;did:claw&gt;/full</code> and checks
                    its mapping state against <code className="rounded bg-slate-900 px-1">log_head.state_hash</code>.
                  </div>
                </div>
                <button
                  onClick={() => void fetchFull(resp?.did_claw || didClaw.trim())}
                  disabled={fullLoading || !resp}
                  className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800/40 disabled:opacity-60"
                >
                  {fullLoading ? 'Fetching…' : 'Fetch /full'}
                </button>
              </div>

              {fullError && (
                <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
                  {fullError}
                </div>
              )}

              {fullResp && (
                <div className="mt-3 space-y-2 text-sm">
                  <CopyableValue label="server" value={fullResp.server} />
                  <CopyableValue label="address" value={fullResp.address} />
                  {fullResp.handle ? <CopyableValue label="handle" value={fullResp.handle} /> : null}
                  {stateHash ? <CopyableValue label="computed_state_hash" value={stateHash} /> : null}
                  {resp?.log_head?.state_hash ? (
                    <CopyableValue label="log_head.state_hash" value={resp.log_head.state_hash} />
                  ) : null}

                  {stateHashStatus === 'PASS' ? (
                    <div className="text-sm text-emerald-200">State hash matches log head commitment.</div>
                  ) : stateHashStatus === 'FAIL' ? (
                    <div className="text-sm text-rose-200">
                      State hash does not match log head commitment. Refetch <code>/key</code> and <code>/full</code>
                      (mapping may have changed), or treat as security relevant.
                    </div>
                  ) : stateHashStatus === 'DEGRADED' ? (
                    <div className="text-sm text-amber-200">
                      Cannot verify state hash (missing <code>log_head</code>).
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
            <h2 className="text-sm font-semibold text-white">Raw JSON</h2>
            <pre className="mt-3 max-h-[420px] overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-200">
              {resp ? JSON.stringify(resp, null, 2) : ''}
            </pre>
          </div>
        </div>
      )}

      <div className="text-xs text-slate-500">
        API base: <span className="font-mono">{apiBase}</span> (override with{' '}
        <span className="font-mono">VITE_CLAWDID_API_BASE</span>)
      </div>
    </div>
  )
}
