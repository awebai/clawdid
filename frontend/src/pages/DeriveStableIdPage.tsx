import { useState } from 'react'
import { didKeyToStableId } from '../lib/stable'

export default function DeriveStableIdPage() {
  const [didKey, setDidKey] = useState('')
  const [stableClaw, setStableClaw] = useState<string | null>(null)
  const [stableAw, setStableAw] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onDerive() {
    const dk = didKey.trim()
    setError(null)
    setStableClaw(null)
    setStableAw(null)
    if (!dk) return
    setLoading(true)
    try {
      const claw = await didKeyToStableId(dk, 'claw')
      const aw = await didKeyToStableId(dk, 'aw')
      setStableClaw(claw)
      setStableAw(aw)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
        <h1 className="text-lg font-semibold text-white">Derive stable ID</h1>
        <p className="mt-1 text-sm text-slate-400">
          Computes <code className="rounded bg-slate-900 px-1">did:claw</code> and{' '}
          <code className="rounded bg-slate-900 px-1">did:aw</code> from the Ed25519 public key embedded in a{' '}
          <code className="rounded bg-slate-900 px-1">did:key</code>.
        </p>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={didKey}
            onChange={(e) => setDidKey(e.target.value)}
            placeholder="did:key:z..."
            className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500/50"
          />
          <button
            onClick={onDerive}
            disabled={loading}
            className="rounded-xl bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400 disabled:opacity-60"
          >
            {loading ? 'Deriving…' : 'Derive'}
          </button>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">
            {error}
          </div>
        )}
      </div>

      {(stableClaw || stableAw) && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
            <div className="text-xs text-slate-500">did:claw</div>
            <div className="mt-2 break-all font-mono text-sm text-slate-200">{stableClaw}</div>
          </div>
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/40 p-5">
            <div className="text-xs text-slate-500">did:aw</div>
            <div className="mt-2 break-all font-mono text-sm text-slate-200">{stableAw}</div>
          </div>
        </div>
      )}
    </div>
  )
}

