import React, { useState, useEffect } from 'react';
import {
  Bell, Search, Filter, AlertTriangle, AlertCircle, CheckCircle,
  ChevronDown, X, Info, Clock, Server, Shield, Database, RefreshCw,
  ExternalLink, Layers, ShieldAlert, Check, UserX, Eye
} from 'lucide-react';
import { fetchRealNotifications, type NotificationItem } from '../../api/dashboard';

export default function Alerts() {
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState<any>(null);
  const [alertsList, setAlertsList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data: NotificationItem[] = await fetchRealNotifications();
      const formatted = data.map(item => ({
        id: item.id,
        type: item.type || 'info',
        severity: item.severity || (item.type === 'critical' ? 'critical' : 'info'),
        title: item.title,
        message: item.message || item.title,
        category: item.category || 'General',
        source: item.source || 'ERAOP System',
        time: item.timestamp,
        status: item.is_read ? 'Acknowledged' : 'Open',
        mitigation: item.mitigation || 'Inspect active telemetry and verify administrative actions.',
        affected: item.affected || 'Enterprise Platform'
      }));
      setAlertsList(formatted);
      setLastRefreshed(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (e) {
      console.error('Failed to load notifications:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  // Compute category options dynamically
  const categories = Array.from(new Set(alertsList.map(a => a.category).filter(Boolean)));
  const sources = Array.from(new Set(alertsList.map(a => a.source).filter(Boolean)));

  const filteredAlerts = alertsList.filter(alert => {
    const textToMatch = `${alert.title} ${alert.message} ${alert.category} ${alert.source}`.toLowerCase();
    const matchesSearch = textToMatch.includes(searchTerm.toLowerCase());
    const matchesSeverity = severityFilter === 'all' || alert.type === severityFilter || alert.severity === severityFilter;
    const matchesCategory = categoryFilter === 'all' || alert.category === categoryFilter;
    const matchesSource = sourceFilter === 'all' || alert.source === sourceFilter;
    return matchesSearch && matchesSeverity && matchesCategory && matchesSource;
  });

  const criticalCount = alertsList.filter(a => a.type === 'critical' || a.severity === 'critical').length;
  const warningCount = alertsList.filter(a => a.type === 'warning' || a.severity === 'high' || a.severity === 'medium').length;
  const supabaseAdminCount = alertsList.filter(a => a.source?.includes('Supabase')).length;

  const getCategoryBadgeClass = (category: string) => {
    const c = category.toLowerCase();
    if (c.includes('suspension') || c.includes('block') || c.includes('security')) {
      return 'bg-red-500/10 text-red-400 border border-red-500/30';
    }
    if (c.includes('approval') || c.includes('resumed')) {
      return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
    }
    if (c.includes('review') || c.includes('pending')) {
      return 'bg-amber-500/10 text-amber-400 border border-amber-500/30';
    }
    if (c.includes('database') || c.includes('connectivity')) {
      return 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30';
    }
    if (c.includes('server')) {
      return 'bg-blue-500/10 text-blue-400 border border-blue-500/30';
    }
    return 'bg-violet-500/10 text-violet-400 border border-violet-500/30';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-textPrimary flex items-center">
            <Bell className="w-7 h-7 mr-3 text-primary animate-pulse" />
            System Alerts &amp; Notification Center
          </h1>
          <p className="text-textSecondary mt-1 text-sm">
            Unified live alerts from Supabase Admin, Target Database, Server Infrastructure, and Security Defense.
            {lastRefreshed && <span className="ml-2 opacity-70">· Updated {lastRefreshed}</span>}
          </p>
        </div>

        <button
          onClick={loadAlerts}
          disabled={loading}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-surface border border-border hover:bg-surfaceHover text-textPrimary text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-primary ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Refreshing...' : 'Refresh Feed'}</span>
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-4 border-l-4 border-l-primary flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-textSecondary font-semibold uppercase">
            <span>Total Active Alerts</span>
            <Bell className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-2">{alertsList.length}</div>
          <div className="text-[11px] text-textSecondary mt-1">Aggregated across all feeds</div>
        </div>

        <div className="glass-card p-4 border-l-4 border-l-danger flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-danger font-semibold uppercase">
            <span>Critical Incidents</span>
            <AlertCircle className="w-4 h-4 text-danger animate-pulse" />
          </div>
          <div className="text-2xl font-bold text-danger mt-2">{criticalCount}</div>
          <div className="text-[11px] text-danger/80 mt-1">Immediate action required</div>
        </div>

        <div className="glass-card p-4 border-l-4 border-l-warning flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-warning font-semibold uppercase">
            <span>Warnings &amp; Reviews</span>
            <AlertTriangle className="w-4 h-4 text-warning" />
          </div>
          <div className="text-2xl font-bold text-warning mt-2">{warningCount}</div>
          <div className="text-[11px] text-textSecondary mt-1">Review pending items</div>
        </div>

        <div className="glass-card p-4 border-l-4 border-l-cyan-500 flex flex-col justify-between">
          <div className="flex justify-between items-center text-xs text-cyan-400 font-semibold uppercase">
            <span>Supabase Admin Alerts</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2">{supabaseAdminCount}</div>
          <div className="text-[11px] text-textSecondary mt-1">Remote cloud admin stream</div>
        </div>
      </div>

      {/* Filters and Table Panel */}
      <div className="glass-panel p-6 border border-border shadow-lg">
        {/* Search and Filters Bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
          {/* Search Input */}
          <div className="md:col-span-1 relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-textSecondary" />
            </div>
            <input
              type="text"
              placeholder="Search by keyword, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full pl-9 pr-3 py-2 border border-border rounded-xl bg-surface text-textPrimary placeholder-textSecondary text-xs focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all"
            />
          </div>

          {/* Severity Filter */}
          <div className="relative">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="appearance-none block w-full bg-surface border border-border text-textPrimary py-2 pl-3 pr-8 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer transition-all"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical Only</option>
              <option value="warning">Warning Only</option>
              <option value="info">Info Only</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-textSecondary" />
          </div>

          {/* Category Filter */}
          <div className="relative">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="appearance-none block w-full bg-surface border border-border text-textPrimary py-2 pl-3 pr-8 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer transition-all"
            >
              <option value="all">All Categories</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-textSecondary" />
          </div>

          {/* Source Filter */}
          <div className="relative">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="appearance-none block w-full bg-surface border border-border text-textPrimary py-2 pl-3 pr-8 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer transition-all"
            >
              <option value="all">All Sources</option>
              {sources.map(src => (
                <option key={src} value={src}>{src}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-textSecondary" />
          </div>
        </div>

        {/* Alerts Table */}
        <div className="overflow-x-auto rounded-xl border border-border/80">
          <table className="w-full text-xs text-left">
            <thead className="text-[11px] text-textSecondary uppercase bg-surfaceHover/80 border-b border-border">
              <tr>
                <th className="px-5 py-3.5">Severity</th>
                <th className="px-5 py-3.5">Category</th>
                <th className="px-5 py-3.5">Notification Title &amp; Details</th>
                <th className="px-5 py-3.5">Source</th>
                <th className="px-5 py-3.5">Timestamp</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-background/50">
              {filteredAlerts.length > 0 ? (
                filteredAlerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-surfaceHover/60 transition-colors">
                    {/* Severity */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        alert.type === 'critical' ? 'bg-danger/15 text-danger border border-danger/30 shadow-[0_0_10px_rgba(227,6,19,0.2)]' :
                        alert.type === 'warning' ? 'bg-warning/15 text-warning border border-warning/30' :
                        'bg-success/15 text-success border border-success/30'
                      }`}>
                        {alert.type === 'critical' ? (
                          <AlertCircle className="w-3.5 h-3.5 animate-pulse" />
                        ) : alert.type === 'warning' ? (
                          <AlertTriangle className="w-3.5 h-3.5" />
                        ) : (
                          <CheckCircle className="w-3.5 h-3.5" />
                        )}
                        <span>{alert.type}</span>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-semibold ${getCategoryBadgeClass(alert.category)}`}>
                        {alert.category}
                      </span>
                    </td>

                    {/* Title & Message */}
                    <td className="px-5 py-4 max-w-md">
                      <div className="font-bold text-textPrimary text-xs">{alert.title}</div>
                      <div className="text-textSecondary text-[11px] mt-0.5 line-clamp-2 leading-relaxed">
                        {alert.message}
                      </div>
                    </td>

                    {/* Source */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        {alert.source.includes('Supabase') ? (
                          <span className="w-2 h-2 rounded-full bg-emerald-400" />
                        ) : alert.source.includes('Server') ? (
                          <span className="w-2 h-2 rounded-full bg-cyan-400" />
                        ) : (
                          <span className="w-2 h-2 rounded-full bg-primary" />
                        )}
                        <span className="text-textPrimary font-medium text-xs">{alert.source}</span>
                      </div>
                    </td>

                    {/* Time */}
                    <td className="px-5 py-4 whitespace-nowrap text-textSecondary font-mono text-[11px]">
                      {alert.time}
                    </td>

                    {/* Status */}
                    <td className="px-5 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        alert.status === 'Open' ? 'bg-primary/10 text-primary border border-primary/30' :
                        alert.status === 'Investigating' ? 'bg-warning/10 text-warning border border-warning/30' :
                        'bg-success/10 text-success border border-success/30'
                      }`}>
                        {alert.status}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="px-5 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => setSelectedAlert(alert)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-surface hover:bg-surfaceHover border border-border text-primary hover:text-primary font-semibold text-xs transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-14 text-center text-textSecondary">
                    <div className="max-w-sm mx-auto">
                      <CheckCircle className="w-10 h-10 text-success mx-auto mb-2 opacity-50" />
                      <p className="font-semibold text-textPrimary text-sm">No Alerts Found</p>
                      <p className="text-xs text-textSecondary mt-1">There are no notifications matching the selected criteria.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alert Detail Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-surface border border-border p-6 rounded-2xl w-full max-w-xl shadow-2xl relative overflow-hidden">
            {/* Top Accent Line */}
            <div className={`absolute top-0 inset-x-0 h-1.5 ${
              selectedAlert.type === 'critical' ? 'bg-danger' :
              selectedAlert.type === 'warning' ? 'bg-warning' : 'bg-success'
            }`} />

            <button
              onClick={() => setSelectedAlert(null)}
              className="absolute top-4 right-4 text-textSecondary hover:text-textPrimary p-1 rounded-lg hover:bg-surfaceHover transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="flex items-start space-x-3 mb-6 pr-8">
              <div className={`p-3 rounded-2xl border ${
                selectedAlert.type === 'critical' ? 'bg-danger/15 border-danger/30 text-danger' :
                selectedAlert.type === 'warning' ? 'bg-warning/15 border-warning/30 text-warning' :
                'bg-success/15 border-success/30 text-success'
              }`}>
                {selectedAlert.type === 'critical' ? <AlertCircle className="w-6 h-6 animate-pulse" /> :
                 selectedAlert.type === 'warning' ? <AlertTriangle className="w-6 h-6" /> :
                 <CheckCircle className="w-6 h-6" />}
              </div>
              <div>
                <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase mb-1 ${getCategoryBadgeClass(selectedAlert.category)}`}>
                  {selectedAlert.category}
                </span>
                <h3 className="text-lg font-bold text-textPrimary leading-snug">{selectedAlert.title}</h3>
                <p className="text-xs text-textSecondary mt-0.5">{selectedAlert.source} • {selectedAlert.time}</p>
              </div>
            </div>

            {/* Content Details */}
            <div className="space-y-4">
              <div className="bg-background/80 rounded-xl p-4 border border-border space-y-3">
                <div>
                  <label className="text-[10px] font-bold uppercase text-textSecondary tracking-wider block mb-1">
                    Notification Message
                  </label>
                  <p className="text-xs text-textPrimary leading-relaxed font-medium bg-surface/50 p-2.5 rounded-lg border border-border">
                    {selectedAlert.message}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="text-[10px] font-bold uppercase text-textSecondary tracking-wider block mb-1">
                      Target Entity / Audience
                    </label>
                    <p className="text-xs text-textPrimary font-mono">
                      {selectedAlert.affected}
                    </p>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold uppercase text-textSecondary tracking-wider block mb-1">
                      Event Source
                    </label>
                    <p className="text-xs text-textPrimary font-semibold">
                      {selectedAlert.source}
                    </p>
                  </div>
                </div>

                <div className="pt-2 border-t border-border/60">
                  <label className="text-[10px] font-bold uppercase text-textSecondary tracking-wider block mb-1">
                    Recommended Mitigation
                  </label>
                  <div className="flex items-start space-x-2 text-xs text-textPrimary">
                    <Check className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                    <span>{selectedAlert.mitigation}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 flex justify-between items-center">
                <span className={`text-xs font-semibold px-3 py-1 rounded-full border ${
                  selectedAlert.status === 'Open' ? 'bg-primary/10 border-primary/30 text-primary' :
                  selectedAlert.status === 'Investigating' ? 'bg-warning/10 border-warning/30 text-warning' :
                  'bg-success/10 border-success/30 text-success'
                }`}>
                  Current Status: {selectedAlert.status}
                </span>

                <div className="flex items-center space-x-2">
                  {selectedAlert.status !== 'Acknowledged' && (
                    <button
                      onClick={() => {
                        setSelectedAlert({ ...selectedAlert, status: 'Acknowledged' });
                        setAlertsList(prev => prev.map(a => a.id === selectedAlert.id ? { ...a, status: 'Acknowledged' } : a));
                      }}
                      className="px-3.5 py-1.5 bg-surfaceHover border border-border hover:bg-border text-textPrimary text-xs font-semibold rounded-xl transition-colors"
                    >
                      Acknowledge
                    </button>
                  )}
                  <button
                    onClick={() => setSelectedAlert(null)}
                    className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded-xl hover:bg-primary/90 transition-colors shadow-sm"
                  >
                    Done
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
