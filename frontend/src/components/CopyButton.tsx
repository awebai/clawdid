import { useEffect, useState } from 'react'

export default function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle')

  useEffect(() => {
    if (status === 'idle') return
    const t = window.setTimeout(() => setStatus('idle'), 1200)
    return () => window.clearTimeout(t)
  }, [status])

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(value)
      setStatus('copied')
    } catch {
      setStatus('failed')
    }
  }

  return (
    <button
      type="button"
      onClick={onCopy}
      className="rounded-md border border-slate-800/80 bg-slate-950/60 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800/40 disabled:opacity-60"
      disabled={!value}
    >
      {status === 'copied' ? 'Copied' : status === 'failed' ? 'Copy failed' : label}
    </button>
  )
}

