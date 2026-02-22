import { Link, Route, Routes } from 'react-router-dom'
import LookupPage from './pages/LookupPage'
import VerifyLogPage from './pages/VerifyLogPage'
import DeriveStableIdPage from './pages/DeriveStableIdPage'

function NavLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="rounded-md px-3 py-2 text-sm text-slate-200 hover:bg-slate-800/60"
    >
      {label}
    </Link>
  )
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800/70 bg-slate-950/40 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-400" />
            <div className="leading-tight">
              <div className="text-sm font-semibold text-white">clawdid</div>
              <div className="text-xs text-slate-400">stable identity registry</div>
            </div>
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" label="Lookup" />
            <NavLink to="/verify-log" label="Verify Log" />
            <NavLink to="/derive" label="Derive ID" />
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<LookupPage />} />
          <Route path="/verify-log" element={<VerifyLogPage />} />
          <Route path="/derive" element={<DeriveStableIdPage />} />
        </Routes>
      </main>

      <footer className="border-t border-slate-800/70 py-8">
        <div className="mx-auto max-w-5xl px-4 text-xs text-slate-500">
          <div className="flex flex-wrap items-center gap-3">
            <span>© {new Date().getFullYear()} ClaWDID</span>
            <a
              className="hover:text-slate-300"
              href="http://127.0.0.1:18111/docs"
              target="_blank"
              rel="noreferrer"
            >
              Local API docs
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

