import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCircle, AlertTriangle, AlertCircle, Moon, Sun, Menu, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';

import { fetchRealNotifications, type NotificationItem } from '../../api/dashboard';

interface HeaderProps {
  onMenuToggle?: () => void;
  isCollapsed?: boolean;
  onDesktopToggle?: () => void;
}

export default function Header({ onMenuToggle, isCollapsed, onDesktopToggle }: HeaderProps) {
  const { userEmail, logout, role, avatar } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [currentAvatar, setCurrentAvatar] = useState<string | null>(() => {
    return avatar || localStorage.getItem('auth_avatar');
  });
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (avatar) {
      setCurrentAvatar(avatar);
    } else {
      const stored = localStorage.getItem('auth_avatar');
      if (stored) setCurrentAvatar(stored);
    }
  }, [avatar]);

  useEffect(() => {
    const handleAvatarSync = () => {
      const stored = localStorage.getItem('auth_avatar');
      setCurrentAvatar(stored);
    };
    window.addEventListener('auth_avatar_changed', handleAvatarSync);
    window.addEventListener('storage', handleAvatarSync);
    const userPhoto = avatar || currentAvatar || localStorage.getItem('auth_avatar');

  return () => {
      window.removeEventListener('auth_avatar_changed', handleAvatarSync);
      window.removeEventListener('storage', handleAvatarSync);
    };
  }, []);

  useEffect(() => {
    fetchRealNotifications().then(data => setNotifications(data));
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    const userPhoto = avatar || currentAvatar || localStorage.getItem('auth_avatar');

  return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);





  const userPhoto = avatar || currentAvatar || localStorage.getItem('auth_avatar');

  return (
    <header className="h-16 bg-surface/80 backdrop-blur-md border-b border-border flex items-center justify-between px-4 md:px-6 sticky top-0 z-10 w-full">
      <div className="flex flex-1 items-center space-x-2 md:space-x-4">
        {onMenuToggle && (
          <button 
            onClick={onMenuToggle}
            className="md:hidden p-2 text-textSecondary hover:text-textPrimary transition-colors rounded-lg hover:bg-surfaceHover"
            title="Open Menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {onDesktopToggle && (
          <button 
            onClick={onDesktopToggle}
            className="hidden md:block p-2 text-textSecondary hover:text-textPrimary transition-colors rounded-lg hover:bg-surfaceHover"
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        <div className="flex items-center space-x-3 ml-2">
          <img 
            src="/assets/brand/logo.svg" 
            alt="Red Cloud ICT Solutions"
            className="h-7 w-auto object-contain hidden sm:block" 
            onError={(e) => {
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
          <div className="hidden lg:flex items-center space-x-2 pl-3 border-l border-border/60">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold text-textSecondary">Red Cloud ICT Solutions • Enterprise Platform</span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center space-x-4">
        <button
          onClick={toggleTheme}
          className="p-2 text-textSecondary hover:text-textPrimary transition-colors rounded-full hover:bg-surfaceHover"
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
        >
          {theme === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
        </button>
        
        <div className="relative" ref={dropdownRef}>
          <button 
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-textSecondary hover:text-textPrimary transition-colors rounded-full hover:bg-surfaceHover"
            title="Notifications"
            aria-label={`Notifications${notifications.filter(n => !n.is_read).length > 0 ? ` (${notifications.filter(n => !n.is_read).length} unread)` : ''}`}
          >
            <Bell className="h-5 w-5" />
            {notifications.filter(n => !n.is_read).length > 0 && (
              <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-danger ring-2 ring-surface" />
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-surface border border-border rounded-xl shadow-lg z-50 overflow-hidden animate-fade-in">
              <div className="p-4 border-b border-border bg-background flex justify-between items-center">
                <h3 className="font-bold text-textPrimary text-sm">Notifications</h3>
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">{notifications.length} Live</span>
              </div>
              <div className="max-h-80 overflow-y-auto custom-scrollbar">
                {notifications.slice(0, 15).map(notif => (
                  <div
                    key={notif.id}
                    onClick={() => {
                      setShowNotifications(false);
                      navigate('/dashboard/alerts');
                    }}
                    className="p-3 border-b border-border hover:bg-surfaceHover/60 transition-colors cursor-pointer flex items-start"
                  >
                    <div className={`mt-0.5 mr-2.5 flex-shrink-0 p-1.5 rounded-full ${
                      notif.type === 'critical' ? 'bg-danger/15 text-danger' :
                      notif.type === 'warning' ? 'bg-warning/15 text-warning' :
                      'bg-success/15 text-success'
                    }`}>
                      {notif.type === 'critical' ? <AlertCircle className="w-3.5 h-3.5 animate-pulse" /> : notif.type === 'warning' ? <AlertTriangle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <span className="text-[10px] font-bold text-primary truncate max-w-[150px]">{notif.category || 'System'}</span>
                        <span className="text-[10px] text-textSecondary flex-shrink-0">{notif.timestamp}</span>
                      </div>
                      <p className="text-xs font-bold text-textPrimary truncate">{notif.title}</p>
                      <p className="text-[11px] text-textSecondary line-clamp-1 mt-0.5">{notif.message}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div 
                onClick={() => {
                  setShowNotifications(false);
                  navigate('/dashboard/alerts');
                }}
                className="p-3 text-center bg-background hover:bg-surfaceHover/50 transition-colors cursor-pointer border-t border-border"
              >
                <p className="text-xs font-medium text-primary">View All Notifications</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="flex items-center space-x-2 md:space-x-3 border-l border-border pl-3 md:pl-4">
          <div 
            onClick={() => navigate('/dashboard/profile')}
            className="flex flex-col justify-center text-right hidden sm:block cursor-pointer group"
          >
            <span className="text-sm font-semibold text-textPrimary group-hover:text-primary transition-colors">
              {userEmail ? userEmail.split('@')[0].split('.')[0].charAt(0).toUpperCase() + userEmail.split('@')[0].split('.')[0].slice(1) : 'Admin'}
            </span>
          </div>
          <div 
            onClick={() => navigate('/dashboard/profile')}
            className="h-9 w-9 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center text-primary font-bold overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary/60 transition-all shadow-sm flex-shrink-0"
            title="Profile & Settings"
          >
            {userPhoto ? (
              <img 
                src={userPhoto} 
                alt="Profile Avatar" 
                className="h-full w-full object-cover rounded-full" 
              />
            ) : (
              <span>{userEmail ? userEmail.charAt(0).toUpperCase() : 'A'}</span>
            )}
          </div>
          <button 
            onClick={logout}
            className="p-2 text-textSecondary hover:text-danger transition-colors rounded-full hover:bg-surfaceHover ml-2"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
