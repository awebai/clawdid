import CopyButton from './CopyButton'

export default function CopyableValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate font-mono text-sm text-slate-200" title={value}>
            {value}
          </div>
        </div>
        <CopyButton value={value} />
      </div>
    </div>
  )
}

