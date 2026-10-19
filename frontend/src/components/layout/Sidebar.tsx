import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Database, 
  Server, 
  Bell, 
  Settings,
  Bot, 
  Shield, 
  X,
  ShieldCheck,
  Sparkles,
  Layers,
  ChevronRight,
  Activity
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import Logo from '../ui/Logo';

interface NavItemConfig {
  name: string;
  path: string;
  icon: any;
  badge?: string;
  badgeColor?: string;
  highlight?: boolean;
}

const coreNavItems: NavItemConfig[] = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Database Monitoring', path: '/dashboard/database', icon: Database },
  { name: 'Server Monitoring', path: '/dashboard/server', icon: Server },
  { name: 'Security Monitoring', path: '/dashboard/security', icon: ShieldCheck, badge: 'Live', badgeColor: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' },
];

const intelligenceItems: NavItemConfig[] = [
  { name: 'AI Assistant', path: '/dashboard/ai', icon: Bot, badge: '3-in-1 RAG', badgeColor: 'bg-primary/20 text-primary border border-primary/30', highlight: true },
  { name: 'System Alerts', path: '/dashboard/alerts', icon: Bell, badge: 'Realtime', badgeColor: 'bg-warning/20 text-warning border border-warning/30' },
];

const managementItems: NavItemConfig[] = [
  { name: 'Settings & Profile', path: '/dashboard/profile', icon: Settings },
];

interface SidebarProps {
  isCollapsed: boolean;
  isOpen?: boolean;
  onClose?: () => void;
}

export default function Sidebar({ isCollapsed, isOpen = false, onClose }: SidebarProps) {
  const { role } = useAuth();
  
  const superAdminItems: NavItemConfig[] = role === 'superadmin' ? [
    { name: 'Audit & Compliance', path: '/dashboard/audit', icon: Shield }
  ] : [];

  const renderNavGroup = (title: string, items: NavItemConfig[]) => (
    <div className="space-y-1 mb-4">
      {!isCollapsed && (
        <div className="px-3 mb-1.5 flex items-center justify-between">
          <span className="text-[10px] font-bold text-textSecondary/70 uppercase tracking-widest">
            {title}
          </span>
          <div className="h-[1px] flex-1 bg-border/40 ml-3"></div>
        </div>
      )}
      {items.map((item) => (
        <NavLink
          key={item.name}
          to={item.path}
          end={item.path === '/dashboard'}
          title={isCollapsed ? item.name : undefined}
          className={({ isActive }) =>
            cn(
              "group relative flex items-center py-2.5 text-sm font-medium rounded-xl transition-all duration-200",
              isCollapsed ? "justify-center px-0 mx-2" : "px-3.5 mx-2",
              isActive 
                ? "bg-gradient-to-r from-primary/20 via-primary/10 to-transparent text-primary font-semibold shadow-sm border border-primary/20 before:absolute before:left-0 before:top-2 before:bottom-2 before:w-1 before:rounded-r-full before:bg-primary before:shadow-[0_0_10px_rgba(239,68,68,0.8)]" 
                : "text-textSecondary hover:bg-surfaceHover/80 hover:text-textPrimary hover:translate-x-0.5"
            )
          }
        >
          {({ isActive }) => (
            <>
              <item.icon className={cn(
                "flex-shrink-0 h-4.5 w-4.5 transition-all duration-200",
                !isCollapsed && "mr-3",
                isActive ? "text-primary scale-110 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]" : "text-textSecondary group-hover:text-textPrimary group-hover:scale-105"
              )} />
              
              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between min-w-0">
                  <span className="truncate">{item.name}</span>
                  {item.badge && (
                    <span className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider flex-shrink-0 ml-1.5",
                      item.badgeColor || "bg-primary/20 text-primary"
                    )}>
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </NavLink>
      ))}
    </div>
  );

  return (
    <aside className={cn(
      "bg-surface/95 backdrop-blur-xl border-r border-border/80 h-screen flex flex-col fixed left-0 top-0 z-50 transition-all duration-300 shadow-2xl",
      isCollapsed ? "w-16" : "w-64",
      "md:translate-x-0",
      isOpen ? "translate-x-0" : "-translate-x-full"
    )}>
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border/70 bg-surface/50">
        <div className="flex items-center space-x-2.5 overflow-hidden">
          <div className="relative p-1.5 rounded-xl bg-gradient-to-br from-red-600/20 to-red-600/5 border border-red-500/30 shadow-inner flex items-center justify-center">
            <Logo size={26} className="flex-shrink-0" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 animate-pulse border-2 border-surface"></span>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <div className="flex items-center space-x-1.5">
                <span className="text-base font-black tracking-tight text-red-600">RED<span className="text-textPrimary font-extrabold">Cloud</span></span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-red-600/20 text-red-500 border border-red-500/30">
                  ENTERPRISE
                </span>
              </div>
              <span className="text-[9px] text-textSecondary font-semibold tracking-wider uppercase">ICT Solutions</span>
            </div>
          )}
        </div>
        {onClose && (
          <button 
            onClick={onClose}
            className="md:hidden p-1.5 text-textSecondary hover:text-textPrimary rounded-lg hover:bg-surfaceHover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
      
      {/* Scrollable Navigation */}
      <div className="flex-1 overflow-y-auto py-4 custom-scrollbar">
        <nav className="space-y-1">
          {renderNavGroup("Core Systems", coreNavItems)}
          {renderNavGroup("AI & Intelligence", intelligenceItems)}
          {renderNavGroup("Administration", [...superAdminItems, ...managementItems])}
        </nav>
      </div>

      {/* System Status Footer */}
      {!isCollapsed ? (
        <div className="p-3 border-t border-border/70 bg-surface/40">
          <div className="p-2.5 rounded-xl bg-surfaceHover/60 border border-border/60 shadow-inner flex flex-col space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-[11px] font-semibold text-textPrimary">Systems Online</span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                100% OK
              </span>
            </div>
            <div className="text-[10px] text-textSecondary/80 flex items-center justify-between font-mono">
              <span>DB • Server • Security</span>
              <span className="text-primary font-semibold capitalize">{role || 'admin'}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3 border-t border-border/70 flex justify-center">
          <span className="relative flex h-2.5 w-2.5" title="All Systems Operational">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
        </div>
      )}
    </aside>
  );
}
