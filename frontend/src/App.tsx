import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import LookupPage from './pages/LookupPage'
import VerifyLogPage from './pages/VerifyLogPage'
import DeriveStableIdPage from './pages/DeriveStableIdPage'

import { useEffect, useMemo, useState } from 'react'

type TopNavItem = { to: string; label: string }

export default function App() {
  const navItems = useMemo<TopNavItem[]>(
    () => [
      { to: '/', label: 'Lookup' },
      { to: '/verify-log', label: 'Verify Log' },
      { to: '/derive', label: 'Derive ID' },
    ],
    [],
  )
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800/70 bg-slate-950/40 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="ClaWDID"
              width={32}
              height={32}
              className="h-8 w-8 rounded-lg object-contain"
            />
            <div className="leading-tight">
              <div className="text-sm font-semibold text-white">clawdid</div>
              <div className="text-xs text-slate-400">stable identity registry</div>
            </div>
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  [
                    'rounded-md px-3 py-2 text-sm',
                    isActive
                      ? 'bg-slate-800/80 text-white'
                      : 'text-slate-200 hover:bg-slate-800/60',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="sm:hidden">
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              className="rounded-md border border-slate-800/80 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800/40"
              aria-expanded={mobileOpen}
              aria-controls="mobile-nav"
            >
              <span className="sr-only">Toggle navigation</span>
              Menu
            </button>
          </div>
        </div>
        {mobileOpen && (
          <div id="mobile-nav" className="border-t border-slate-800/70 bg-slate-950/70 sm:hidden">
            <div className="mx-auto flex max-w-5xl flex-col gap-1 px-4 py-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    [
                      'rounded-md px-3 py-2 text-sm',
                      isActive ? 'bg-slate-800/80 text-white' : 'text-slate-200 hover:bg-slate-800/60',
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        )}
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
