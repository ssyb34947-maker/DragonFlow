import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Home,
  Download,
  Database,
  BarChart3,
  GitBranch,
  Search,
  Menu,
  X,
  BrainCircuit,
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { path: '/', label: '首页', icon: Home },
  { path: '/pipeline', label: '流程总览', icon: GitBranch },
  { path: '/download', label: '数据下载', icon: Download },
  { path: '/process', label: '预处理', icon: Database },
  { path: '/analysis', label: '分析算法', icon: BarChart3 },
  { path: '/model', label: '模型方案', icon: BrainCircuit },
  { path: '/explorer', label: '数据探索', icon: Search },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg">
      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 240 : 64 }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="flex flex-col z-20"
        style={{
          background: 'linear-gradient(180deg, #0F1115 0%, #0A0C10 100%)',
          borderRight: '1px solid rgba(30, 41, 59, 0.8)',
        }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-border/60">
          <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-xl border border-primary/25 bg-white/[0.04] animate-pulse-glow">
            <img src="/logo.png" alt="DragonFlow logo" className="h-full w-full object-contain p-1" />
          </div>
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <h1
                  className="text-lg font-bold tracking-tight"
                  style={{ fontFamily: 'var(--font-heading)', color: '#fff' }}
                >
                  DragonFlow
                </h1>
                <p className="text-[10px] text-fg-dim">A股金融大数据分析</p>
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto p-1.5 rounded-lg hover:bg-white/5 transition-colors text-fg-muted"
          >
            {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative ${
                    isActive
                      ? 'text-white'
                      : 'text-fg-muted hover:text-fg hover:bg-white/[0.03]'
                  }`
                }
              >
                {isActive && (
                  <motion.div
                    layoutId="navActive"
                    className="absolute inset-0 rounded-xl"
                    style={{
                      background: 'linear-gradient(135deg, rgba(247,147,26,0.15) 0%, rgba(234,88,12,0.08) 100%)',
                      border: '1px solid rgba(247,147,26,0.25)',
                    }}
                    transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  />
                )}
                <Icon className="w-5 h-5 flex-shrink-0 relative z-10" />
                <AnimatePresence>
                  {sidebarOpen && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      className="text-sm font-medium whitespace-nowrap overflow-hidden relative z-10"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {isActive && sidebarOpen && (
                  <motion.div
                    layoutId="activeDot"
                    className="ml-auto w-1.5 h-1.5 rounded-full relative z-10"
                    style={{
                      background: '#F7931A',
                      boxShadow: '0 0 8px rgba(247,147,26,0.60)',
                    }}
                  />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border/60">
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-[10px] text-fg-dim text-center"
              >
                西南财经大学 · 金融大数据分析与数据可视化课程
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-df relative">
        {/* Subtle grid overlay */}
        <div className="absolute inset-0 bg-grid pointer-events-none opacity-50" />
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="p-6 min-h-full relative z-10"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}
