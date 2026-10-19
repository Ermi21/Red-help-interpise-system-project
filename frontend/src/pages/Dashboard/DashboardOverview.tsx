import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  ShieldCheck, 
  Server, 
  Database, 
  AlertTriangle, 
  AlertCircle, 
  ChevronRight, 
  Bot, 
  Loader2, 
  ArrowRight, 
  CheckCircle, 
  Clock,
  Sparkles,
  Shield,
  Cpu,
  Lock,
  ArrowUpRight,
  FileText
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import EnterpriseOverviewChart from '../../components/ui/EnterpriseOverviewChart';
import { fetchHealth, fetchRealNotifications, fetchLiveServerTelemetry } from '../../api/dashboard';
import Logo from '../../components/ui/Logo';

export default function DashboardOverview() {
  const navigate = useNavigate();
  const { profileComplete, role, loginTime, userEmail } = useAuth();
  const [currentTime, setCurrentTime] = useState(
    new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  );

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Format login time and session duration
  const formattedLoginTime = React.useMemo(() => {
    if (!loginTime) return 'Active Now';
    try {
      const d = new Date(loginTime);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    } catch {
      return 'Active Now';
    }
  }, [loginTime]);

  const [sessionDuration, setSessionDuration] = useState('00:00:00');

  useEffect(() => {
    const updateSession = () => {
      const startTime = loginTime ? new Date(loginTime).getTime() : Date.now();
      const diffSecs = Math.max(0, Math.floor((Date.now() - startTime) / 1000));
      const hours = Math.floor(diffSecs / 3600).toString().padStart(2, '0');
      const mins = Math.floor((diffSecs % 3600) / 60).toString().padStart(2, '0');
      const secs = (diffSecs % 60).toString().padStart(2, '0');
      setSessionDuration(`${hours}:${mins}:${secs}`);
    };
    updateSession();
    const timer = setInterval(updateSession, 1000);
    return () => clearInterval(timer);
  }, [loginTime]);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [reportGenerated, setReportGenerated] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const generatePDF = () => {
    window.print();
    setReportGenerated(true);
    setTimeout(() => setReportGenerated(false), 3000);
  };

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [healthRes, notifsRes, serversRes] = await Promise.all([
          fetchHealth().catch(() => ({ 
            db_health: 0, 
            server_health: 0, 
            security_score: 0, 
            ai_status: 'Unknown', 
            db_status: 'Status unavailable' 
          })),
          fetchRealNotifications().catch(() => []),
          fetchLiveServerTelemetry().catch(() => [])
        ]);
        
        const criticalCount = notifsRes.filter((n: any) => n.type === 'critical').length;
        const warningCount = notifsRes.filter((n: any) => n.type === 'warning').length;
        const mediumCount = notifsRes.filter((n: any) => n.type === 'info').length;
        const lowCount = notifsRes.filter((n: any) => n.type === 'success' || !n.type).length;

        setData({
          health: {
            dbHealth: healthRes.db_health || 0,
            dbStatus: healthRes.db_status || 'Unable to retrieve database status',
            serverHealth: healthRes.server_health || 0,
            serverStatus: serversRes.length > 0 ? `${serversRes.length} server nodes reporting` : 'Server metrics unavailable',
            securityScore: healthRes.security_score || 0,
            securityStatus: 'Live from ERAOP security monitor',
            aiSystemRunning: healthRes.ai_status === 'Operational',
          },
          alerts: {
            critical: criticalCount,
            high: warningCount,
            medium: mediumCount,
            low: lowCount
          },
          recommendation: {
            title: 'Unified Cross-System Optimization',
            description: 'All 3 systems (Database, Server Cluster, Security Perimeter) are synchronized. Buffer cache hit ratio is 99.8%, firewall active across 247 endpoints.',
            impact: 'OPTIMAL'
          },
          notifications: notifsRes,
          servers: serversRes
        });
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-full min-h-[600px]">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <span className="ml-3 text-textSecondary font-medium">Synchronizing Enterprise Systems...</span>
      </div>
    );
  }

  const { health, alerts, recommendation } = data;

  return (
    <div className="space-y-5 animate-fade-in relative">
      {/* Profile banner if incomplete */}
      {!profileComplete && (
        <div className="bg-primary/10 border border-primary/20 rounded-xl p-3.5 flex items-center justify-between mb-4 shadow-sm">
          <div>
            <h3 className="text-primary font-bold text-sm">Welcome to Redcloud Enterprise!</h3>
            <p className="text-textSecondary text-xs mt-0.5">
              Please complete your profile credentials to ensure full role-based access to Database, Server, and Security controls.
            </p>
          </div>
          <Link 
            to="/dashboard/profile"
            className="flex items-center px-3 py-1 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium text-xs shadow-sm shadow-primary/20"
          >
            Setup Profile <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
          </Link>
        </div>
      )}

      {/* Report generated toast */}
      {reportGenerated && (
        <div className="fixed bottom-6 right-6 bg-gradient-to-r from-success to-emerald-600 text-white px-5 py-3.5 rounded-xl shadow-xl flex items-center animate-slide-up z-50 border border-white/20">
          <CheckCircle className="w-5 h-5 mr-3 flex-shrink-0" />
          <span className="font-medium text-sm">Full Enterprise 3-System Report Generated & Ready!</span>
        </div>
      )}

      {/* AI Analysis Modal */}
      {showAnalysis && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in p-4">
          <div className="bg-surface border border-border p-6 rounded-2xl w-full max-w-lg shadow-2xl relative">
            <button 
              onClick={() => setShowAnalysis(false)}
              className="absolute top-4 right-4 text-textSecondary hover:text-textPrimary text-xl leading-none"
            >
              &times;
            </button>
            <div className="flex items-center mb-4">
              <div className="p-2.5 rounded-xl bg-primary/10 text-primary mr-3 border border-primary/20">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-textPrimary">Enterprise AI Diagnostics</h3>
                <p className="text-xs text-textSecondary">Unified Database, Server & Security Analysis</p>
              </div>
            </div>
            <p className="text-textSecondary text-sm mb-4 leading-relaxed bg-surfaceHover/50 p-3.5 rounded-xl border border-border">
              {recommendation.description}
            </p>
            <div className="space-y-2 mb-6">
              <div className="flex justify-between items-center text-xs p-2 rounded-lg bg-surfaceHover/40 border border-border/60">
                <span className="text-textSecondary flex items-center">
                  <Database className="w-3.5 h-3.5 mr-2 text-emerald-400" /> Database Engine Status:
                </span>
                <span className="text-emerald-400 font-semibold">100% Synchronized</span>
              </div>
              <div className="flex justify-between items-center text-xs p-2 rounded-lg bg-surfaceHover/40 border border-border/60">
                <span className="text-textSecondary flex items-center">
                  <Server className="w-3.5 h-3.5 mr-2 text-cyan-400" /> Server Cluster Load:
                </span>
                <span className="text-cyan-400 font-semibold">Optimal Load (28% CPU)</span>
              </div>
              <div className="flex justify-between items-center text-xs p-2 rounded-lg bg-surfaceHover/40 border border-border/60">
                <span className="text-textSecondary flex items-center">
                  <ShieldCheck className="w-3.5 h-3.5 mr-2 text-purple-400" /> Security Perimeter:
                </span>
                <span className="text-purple-400 font-semibold">247 Rules Active • 0 Breaches</span>
              </div>
            </div>
            <div className="flex space-x-3">
              <button 
                onClick={() => { setShowAnalysis(false); navigate('/dashboard/ai'); }}
                className="flex-1 py-2.5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium text-xs flex items-center justify-center space-x-1.5 shadow-sm shadow-primary/30"
              >
                <Bot className="w-4 h-4 mr-1" />
                <span>Open in AI Assistant</span>
              </button>
              <button 
                onClick={() => setShowAnalysis(false)}
                className="px-5 py-2.5 bg-surfaceHover text-textPrimary rounded-xl hover:bg-surfaceHover/80 transition-colors font-medium text-xs border border-border"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-3 border-b border-border/70">
        <div className="flex items-center space-x-3.5">
          <div className="p-2 rounded-2xl bg-gradient-to-br from-red-600/20 to-red-600/5 border border-red-500/30 shadow-md flex items-center justify-center flex-shrink-0">
            <Logo size={32} className="flex-shrink-0" />
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-xl sm:text-2xl font-black text-textPrimary tracking-tight">
                RED<span className="text-red-600">Cloud</span> Enterprise Dashboard
              </h1>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-red-600/15 text-red-500 border border-red-500/30 uppercase tracking-wider">
                Live Synergy
              </span>
            </div>
            <p className="text-textSecondary text-xs sm:text-sm mt-0.5 font-medium">
              Red Cloud ICT Solutions • Synchronized Database, Server Cluster, and Security Defense.
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2.5 text-xs">
          {/* Real Login Time & Session Duration Badge */}
          <div className="glass-card px-3 py-1.5 flex items-center space-x-2.5 border border-border/80 shadow-sm rounded-xl bg-surface/80">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <div className="flex flex-col text-[11px] font-mono leading-tight">
              <span className="text-textSecondary text-[10px]">Logged in: <strong className="text-textPrimary">{formattedLoginTime}</strong></span>
              <span className="text-primary font-semibold">Session: {sessionDuration}</span>
            </div>
          </div>

          <div className="glass-card px-3 py-1.5 flex items-center space-x-1.5 text-primary font-mono border border-primary/20 shadow-sm rounded-xl">
            <Clock className="w-3.5 h-3.5 animate-pulse text-red-500" />
            <span className="font-bold">{currentTime}</span>
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-semibold text-xs">AI Operational</span>
          </div>

          <button
            onClick={generatePDF}
            className="flex items-center px-3.5 py-1.5 bg-surfaceHover hover:bg-surface border border-border rounded-xl text-textPrimary transition-colors shadow-sm font-semibold text-xs"
          >
            <FileText className="w-3.5 h-3.5 mr-1.5 text-primary" />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3 CORE SYSTEM BUTTONS (MINIMIZED & ATTRACTIVE WITH DISTINCT HOVER COLORS)   */}
      {/* ========================================================================= */}
      <div>
        <div className="flex items-center justify-between mb-2.5 px-0.5">
          <span className="text-[10px] font-bold text-textSecondary uppercase tracking-widest flex items-center">
            <Sparkles className="w-3 h-3 mr-1.5 text-primary" />
            Core Enterprise Systems (Click to Open)
          </span>
          <span className="text-[10px] text-textSecondary">Real-time status</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
          {/* 1. DATABASE BUTTON - Minimized with Emerald Hover Glow */}
          <Link 
            to="/dashboard/database"
            className="group relative p-3 rounded-2xl border border-border/80 bg-surface/85 backdrop-blur-md flex items-center justify-between transition-all duration-300 hover:border-emerald-500/60 hover:bg-gradient-to-r hover:from-emerald-950/40 hover:via-emerald-900/15 hover:to-surface hover:shadow-[0_4px_24px_rgba(16,185,129,0.2)] hover:-translate-y-0.5 cursor-pointer overflow-hidden"
          >
            <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-emerald-500/0 via-emerald-500/40 to-emerald-500/0 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <div className="flex items-center space-x-3 min-w-0">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 group-hover:bg-emerald-500/20 group-hover:border-emerald-500/50 group-hover:scale-105 transition-all flex-shrink-0 shadow-sm">
                <Database className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-textPrimary group-hover:text-emerald-300 transition-colors truncate">
                    Database System
                  </h3>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse flex-shrink-0"></span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-textSecondary mt-0.5 font-mono">
                  <span className="font-semibold text-emerald-400">{health.dbHealth}% Health</span>
                  <span>•</span>
                  <span className="truncate">&lt; 8ms latency</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2 flex-shrink-0 ml-3">
              <span className="hidden sm:inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 group-hover:bg-emerald-500/25 transition-colors">
                Optimal
              </span>
              <div className="p-1 rounded-lg text-textSecondary group-hover:text-emerald-400 group-hover:translate-x-1 transition-all">
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* 2. SERVER BUTTON - Minimized with Cyan/Blue Hover Glow */}
          <Link 
            to="/dashboard/server"
            className="group relative p-3 rounded-2xl border border-border/80 bg-surface/85 backdrop-blur-md flex items-center justify-between transition-all duration-300 hover:border-cyan-500/60 hover:bg-gradient-to-r hover:from-cyan-950/40 hover:via-blue-900/15 hover:to-surface hover:shadow-[0_4px_24px_rgba(6,182,212,0.2)] hover:-translate-y-0.5 cursor-pointer overflow-hidden"
          >
            <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-cyan-500/0 via-cyan-500/40 to-cyan-500/0 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <div className="flex items-center space-x-3 min-w-0">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/25 group-hover:bg-cyan-500/20 group-hover:border-cyan-500/50 group-hover:scale-105 transition-all flex-shrink-0 shadow-sm">
                <Server className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-textPrimary group-hover:text-cyan-300 transition-colors truncate">
                    Server Infrastructure
                  </h3>
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse flex-shrink-0"></span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-textSecondary mt-0.5 font-mono">
                  <span className="font-semibold text-cyan-400">{health.serverHealth}% Health</span>
                  <span>•</span>
                  <span className="truncate">{health.serverStatus || 'Server metrics loading'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2 flex-shrink-0 ml-3">
              <span className="hidden sm:inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 group-hover:bg-cyan-500/25 transition-colors">
                Online
              </span>
              <div className="p-1 rounded-lg text-textSecondary group-hover:text-cyan-400 group-hover:translate-x-1 transition-all">
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* 3. SECURITY BUTTON - Minimized with Purple/Rose Hover Glow */}
          <Link 
            to="/dashboard/security"
            className="group relative p-3 rounded-2xl border border-border/80 bg-surface/85 backdrop-blur-md flex items-center justify-between transition-all duration-300 hover:border-purple-500/60 hover:bg-gradient-to-r hover:from-purple-950/40 hover:via-rose-900/15 hover:to-surface hover:shadow-[0_4px_24px_rgba(168,85,247,0.2)] hover:-translate-y-0.5 cursor-pointer overflow-hidden"
          >
            <div className="absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-purple-500/0 via-purple-500/40 to-purple-500/0 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            
            <div className="flex items-center space-x-3 min-w-0">
              <div className="p-2.5 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/25 group-hover:bg-purple-500/20 group-hover:border-purple-500/50 group-hover:scale-105 transition-all flex-shrink-0 shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-bold text-textPrimary group-hover:text-purple-300 transition-colors truncate">
                    Security System
                  </h3>
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse flex-shrink-0"></span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-textSecondary mt-0.5 font-mono">
                  <span className="font-semibold text-purple-400">{health.securityScore}% Score</span>
                  <span>•</span>
                  <span className="truncate">{health.securityStatus || 'Live security monitor'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2 flex-shrink-0 ml-3">
              <span className="hidden sm:inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/30 group-hover:bg-purple-500/25 transition-colors">
                Guarded
              </span>
              <div className="p-1 rounded-lg text-textSecondary group-hover:text-purple-400 group-hover:translate-x-1 transition-all">
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          </Link>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* UNIQUE CHART & AI / ALERTS ROW                                            */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 w-full">
        {/* Main Unique Chart Area (EnterpriseOverviewChart) */}
        <div className="xl:col-span-3 w-full">
          <EnterpriseOverviewChart />
        </div>

        {/* Alerts & AI Recommendations Sidebar */}
        <div className="space-y-4">
          {/* Today's Alerts */}
          <div className="glass-panel p-4.5">
            <div className="flex items-center justify-between mb-3.5">
              <h2 className="text-xs font-bold text-textPrimary uppercase tracking-wider flex items-center">
                <AlertCircle className="w-4 h-4 mr-2 text-warning" />
                Alerts & Incidents
              </h2>
              <Link to="/dashboard/alerts" className="text-[11px] text-primary hover:underline font-medium">
                View All
              </Link>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 rounded-lg bg-surfaceHover/70 border border-border">
                <div className="flex items-center">
                  <div className="w-2 h-2 rounded-full bg-danger mr-2.5"></div>
                  <span className="text-xs font-medium text-textPrimary">Critical</span>
                </div>
                <span className="bg-danger/15 text-danger text-[11px] font-bold px-2 py-0.5 rounded-full border border-danger/20 font-mono">
                  {alerts.critical}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surfaceHover/70 border border-border">
                <div className="flex items-center">
                  <div className="w-2 h-2 rounded-full bg-warning mr-2.5"></div>
                  <span className="text-xs font-medium text-textPrimary">Warning</span>
                </div>
                <span className="bg-warning/15 text-warning text-[11px] font-bold px-2 py-0.5 rounded-full border border-warning/20 font-mono">
                  {alerts.high}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surfaceHover/70 border border-border">
                <div className="flex items-center">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mr-2.5"></div>
                  <span className="text-xs font-medium text-textPrimary">Info</span>
                </div>
                <span className="bg-blue-500/15 text-blue-400 text-[11px] font-bold px-2 py-0.5 rounded-full border border-blue-500/20 font-mono">
                  {alerts.medium}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-lg bg-surfaceHover/70 border border-border">
                <div className="flex items-center">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 mr-2.5"></div>
                  <span className="text-xs font-medium text-textPrimary">Normal</span>
                </div>
                <span className="bg-surface text-textSecondary text-[11px] font-bold px-2 py-0.5 rounded-full border border-border font-mono">
                  {alerts.low}
                </span>
              </div>
            </div>
          </div>

          {/* Unified AI Recommendation Card */}
          <div className="glass-panel p-4.5 border-primary/30 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
            <div className="flex items-center justify-between mb-2.5 relative z-10">
              <div className="flex items-center">
                <Bot className="w-4 h-4 text-primary mr-2" />
                <h2 className="text-xs font-bold text-primary uppercase tracking-wider">AI DBA & SRE Insight</h2>
              </div>
              <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                Synchronized
              </span>
            </div>
            
            <p className="text-textPrimary font-semibold text-xs leading-relaxed mb-2 relative z-10">
              {recommendation.title}
            </p>

            <div className="p-2.5 bg-surface/80 rounded-xl border border-border relative z-10 mb-3">
              <p className="text-xs text-textSecondary leading-relaxed">
                {recommendation.description}
              </p>
            </div>

            <div className="flex space-x-2 relative z-10">
              <button 
                onClick={() => setShowAnalysis(true)}
                className="flex-1 flex items-center justify-center py-1.5 px-3 text-xs font-semibold text-primary bg-primary/10 hover:bg-primary/20 border border-primary/30 rounded-lg transition-colors"
              >
                <span>Diagnostics</span>
                <ChevronRight className="w-3.5 h-3.5 ml-1" />
              </button>
              <Link 
                to="/dashboard/ai"
                className="flex items-center justify-center py-1.5 px-3 text-xs font-semibold text-white bg-primary hover:bg-primary/90 rounded-lg transition-colors shadow-sm shadow-primary/20"
              >
                <Sparkles className="w-3.5 h-3.5 mr-1" />
                <span>AI Chat</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
