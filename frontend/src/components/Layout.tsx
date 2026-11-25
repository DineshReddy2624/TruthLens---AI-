import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { Menu, ShieldCheck } from 'lucide-react';

export default function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  // Close mobile drawer on route transition
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const getPageTitle = (path: string) => {
    if (path === '/dashboard') return 'Verification Dashboard';
    if (path.startsWith('/verify/claim')) return 'Verify Claim';
    if (path.startsWith('/verify/article')) return 'Verify Article';
    if (path.startsWith('/verify/file')) return 'Document Upload';
    if (path.startsWith('/verify/url')) return 'URL Verification';
    if (path.startsWith('/requests/')) return 'Verification Report Details';
    if (path.startsWith('/history')) return 'Verification History';
    if (path.startsWith('/admin')) return 'Administrator Console';
    return 'TruthLens AI';
  };

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans text-slate-800">
      {/* Sidebar Navigation */}
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Mobile Top Header (Small screens only) */}
        <header className="lg:hidden bg-slate-900 border-b border-slate-800 px-4 py-3 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-white" />
            </div>
            <span className="text-white font-bold tracking-tight text-sm">TruthLens AI</span>
          </div>
          <button
            onClick={() => setMobileOpen(true)}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Open Navigation Menu"
          >
            <Menu size={20} />
          </button>
        </header>

        {/* Desktop Top Header Bar */}
        <header className="hidden lg:flex items-center justify-between bg-white border-b border-slate-200/80 px-8 py-3.5 sticky top-0 z-20 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <h2 className="text-sm font-bold text-slate-800 tracking-tight">
              {getPageTitle(location.pathname)}
            </h2>
            <span className="text-slate-300">&bull;</span>
            <span className="text-xs text-slate-400 font-medium">
              Multi-Agent Fact Verification Platform
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>10 Agents Active</span>
            </div>
          </div>
        </header>

        {/* Page Content Body */}
        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Minimal Footer */}
        <footer className="bg-white border-t border-slate-200/80 py-4 px-8 text-center text-xs text-slate-400">
          <p>
            TruthLens AI &bull; Autonomous Multi-Agent Verification &bull; DeBERTa MNLI + Cross-Encoder Reranking
          </p>
        </footer>
      </div>
    </div>
  );
}
