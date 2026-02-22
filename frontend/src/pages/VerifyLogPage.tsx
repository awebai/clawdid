import { useMemo, useState } from 'react'
import { apiBaseUrl } from '../lib/config'
import { fetchJson } from '../lib/http'
import { verifyLogEntries, type DidLogEntry } from '../lib/clawdid'
import { isStableId } from '../lib/stable'

function StatusPill({ ok }: { ok: boolean }) {
  const cls = ok
    ? 'bg-emerald-500/15 text-emerald-200 ring-1 ring-emerald-500/30'
    : 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/30'
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs ${cls}`}>
      {ok ? 'VERIFIED' : 'FAILED'}
    </span>
  )
}

export default function VerifyLogPage() {
  const apiBase = useMemo(() => apiBaseUrl(), [])
  const [didClaw, setDidClaw] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entries, setEntries] = useState<DidLogEntry[] | null>(null)
  const [result, setResult] = useState<{ ok: boolean; errors: string[] } | null>(null)

  async function onVerify() {
    const id = didClaw.trim()
    setError(null)
    setEntries(null)
    setResult(null)
    if (!id) return
    if (!isStableId(id)) {
      setError('Stable ID must start with did:claw: or did:aw:.')
      return
    }
    setLoading(true)
    try {
      const body = await fetchJson<DidLogEntry[]>(`${apiBase}/did/${encodeURIComponent(id)}/log`)
      setEntries(body)
      const r = await verifyLogEntries(body)
      setResult(r)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
        <h1 className="text-lg font-semibold text-white">Verify audit log</h1>
        <p className="mt-1 text-sm text-slate-400">
          Fetches <code className="rounded bg-slate-900 px-1">/did/&lt;did:claw&gt;/log</code> and verifies each
          entry hash, signature, and the hash chain.
        </p>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={didClaw}
            onChange={(e) => setDidClaw(e.target.value)}
            placeholder="did:claw:..."
            className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500/50"
            onKeyDown={(e) => {
              if (e.key === 'Enter') void onVerify()
            }}
          />
          <button
            onClick={onVerify}
            disabled={loading}
            className="rounded-xl bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-60"
          >
            {loading ? 'Verifying…' : 'Verify'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-slate-300">
              Entries: <span className="font-mono">{entries?.length ?? 0}</span>
            </div>
            <StatusPill ok={result.ok} />
          </div>
        )}

        {result && !result.ok && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-rose-200">
            {result.errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      {entries && (
        <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
          <h2 className="text-sm font-semibold text-white">Entries</h2>
          <pre className="mt-3 max-h-[520px] overflow-auto rounded-xl bg-slate-950/70 p-3 text-xs text-slate-200">
            {JSON.stringify(entries, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
