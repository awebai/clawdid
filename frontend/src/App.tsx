import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
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
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-[rgba(148,163,184,0.14)] bg-[#070a12]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3.5">
          <a href="https://clawdid.ai" className="flex items-center gap-2.5">
            <img
              src="/logo.png"
              alt="ClawDID"
              width={64}
              height={64}
              className="rounded-[14px]"
            />
            <span className="text-[26px] font-bold text-white">ClawDID</span>
          </a>
          <nav className="hidden items-center gap-1 text-sm sm:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive
                    ? 'rounded-lg bg-slate-800/60 px-3 py-1.5 text-white'
                    : 'rounded-lg px-3 py-1.5 text-[#94a3b8] hover:bg-slate-800/30 hover:text-white'
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

      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<LookupPage />} />
          <Route path="/verify-log" element={<VerifyLogPage />} />
          <Route path="/derive" element={<DeriveStableIdPage />} />
        </Routes>
      </main>

      <footer className="mt-auto border-t border-[rgba(148,163,184,0.14)] py-6">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-4 text-xs text-slate-400">
          <span>© {new Date().getFullYear()} ClawDID</span>
          <a className="hover:text-slate-200" href="https://clawdid.ai" target="_blank" rel="noreferrer">
            clawdid.ai
          </a>
          <a className="hover:text-slate-200" href="https://clawdid.ai/docs/" target="_blank" rel="noreferrer">
            Docs
          </a>
          <a className="hover:text-slate-200" href="https://api.clawdid.ai/docs" target="_blank" rel="noreferrer">
            Swagger
          </a>
          <a className="hover:text-slate-200" href="https://api.clawdid.ai/openapi.json" target="_blank" rel="noreferrer">
            OpenAPI
          </a>
          <a className="hover:text-slate-200" href="https://github.com/awebai/clawdid" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </div>
      </footer>
    </div>
  )
}
