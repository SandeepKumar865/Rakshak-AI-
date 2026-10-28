import React from 'react';
import {
  LayoutDashboard,
  FileSpreadsheet,
  BarChart3,
  FileText,
  Activity,
  Settings,
  Shield,
  PhoneCall,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  systemStatus?: 'healthy' | 'unhealthy' | 'unavailable';
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  systemStatus = 'healthy',
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'cases', label: 'Complaints / Cases', icon: FileSpreadsheet },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'reports', label: 'Official Reports', icon: FileText },
    { id: 'system', label: 'System Health', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const handleNavClick = (id: string) => {
    onSelectTab(id);
    if (onCloseMobile) onCloseMobile();
  };

  const isHealthy = systemStatus === 'healthy';

  return (
    <>
      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 w-64 bg-white border-r border-slate-200 z-50 flex flex-col transition-transform duration-200 ease-in-out lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-200 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-800 flex items-center justify-center text-white shadow-sm shrink-0">
            <Shield className="w-5 h-5" strokeWidth={2.2} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-base font-extrabold text-slate-900 tracking-tight">
                RAKSHAK
              </span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold font-mono">
                AI
              </span>
            </div>
            <p className="text-[11px] font-medium text-slate-500 leading-tight">
              Cybercrime First Responder
            </p>
          </div>
        </div>

        {/* Live Operational Status Banner */}
        <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200/80 flex items-center justify-between text-xs">
          <span className="text-slate-500 font-medium flex items-center gap-1.5">
            Backend Telephony:
          </span>
          <span
            className={`inline-flex items-center gap-1 font-semibold text-[11px] px-2 py-0.5 rounded-full ${
              isHealthy
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-rose-50 text-rose-700 border border-rose-200'
            }`}
          >
            {isHealthy ? (
              <>
                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                <span>Operational</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3 h-3 text-rose-600" />
                <span>Offline</span>
              </>
            )}
          </span>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? 'text-blue-600' : 'text-slate-400'
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Official Emergency Directive Card */}
        <div className="p-4 m-3 rounded-xl bg-blue-50/70 border border-blue-200/80 space-y-2">
          <div className="flex items-center gap-2 text-blue-900">
            <PhoneCall className="w-4 h-4 text-blue-700" />
            <span className="text-xs font-bold uppercase tracking-wider">
              Emergency Helpline
            </span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">
            Instruct callers to dial <strong className="text-blue-800 font-bold font-mono">1930</strong> immediately to freeze financial frauds in transit.
          </p>
        </div>
      </aside>
    </>
  );
};
