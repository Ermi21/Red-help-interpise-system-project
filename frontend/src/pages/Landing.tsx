import { useNavigate } from 'react-router-dom';
import type { MouseEvent } from 'react';
import { 
  Database, 
  ShieldCheck, 
  Server, 
  Bot, 
  Activity, 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  Cpu, 
  Zap,
  Lock,
  ChevronRight
} from 'lucide-react';
import Logo from '../components/ui/Logo';

export default function Landing() {
  const navigate = useNavigate();

  const handleGetStarted = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#0A0C0E] text-white selection:bg-red-600 selection:text-white relative overflow-hidden cyber-grid-bg">
      {/* Dynamic Ambient Glowing Orbs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-red-600/15 rounded-full blur-[140px] pointer-events-none animate-pulse-glow" />
      <div className="absolute top-1/3 right-10 w-[450px] h-[450px] bg-red-700/10 rounded-full blur-[160px] pointer-events-none animate-float-slow" />
      <div className="absolute bottom-10 left-1/3 w-[600px] h-[600px] bg-emerald-600/10 rounded-full blur-[180px] pointer-events-none" />

      {/* Floating Transparent Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4 transition-all duration-300">
        <div className="max-w-7xl mx-auto flex items-center justify-between glass-frosted rounded-2xl px-6 py-3 border border-white/10 shadow-2xl backdrop-blur-xl">
          {/* Brand Logo */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigate('/')}>
            <Logo size={32} className="flex-shrink-0 animate-float" />
            <div className="flex flex-col">
              <div className="flex items-center space-x-1">
                <span className="text-xl font-black text-red-600 tracking-tight">RED</span>
                <span className="text-xl font-extrabold text-white tracking-tight">Cloud</span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-red-600/20 text-red-400 border border-red-500/30 ml-1">
                  ETHIOPIA
                </span>
              </div>
              <span className="text-[9px] font-semibold text-gray-400 tracking-wider uppercase">ICT Solutions</span>
            </div>
          </div>

          {/* Quick Nav Links */}
          <nav className="hidden md:flex items-center space-x-8 text-sm font-medium text-gray-300">
            <a href="#features" className="hover:text-red-400 transition-colors">Features</a>
            <a href="#architecture" className="hover:text-red-400 transition-colors">Architecture</a>
            <a href="#security" className="hover:text-red-400 transition-colors">Security</a>
            <span className="inline-flex items-center text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse mr-1.5"></span>
              All Systems Live
            </span>
          </nav>

          {/* Sign In Button */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handleGetStarted}
              className="group relative px-6 py-2.5 rounded-xl font-semibold text-sm text-white overflow-hidden shadow-lg transition-all duration-300 hover:scale-105 active:scale-95"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-red-600 to-red-700 transition-all duration-300 group-hover:from-red-500 group-hover:to-red-600" />
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.3)_0%,transparent_70%)]" />
              <span className="relative flex items-center">
                Sign In
                <ArrowRight className="w-4 h-4 ml-1.5 transform group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative pt-36 pb-24 px-6 z-10">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-12 gap-12 items-center">
            {/* Left Column: Hero Copy */}
            <div className="lg:col-span-7 space-y-7 animate-fade-in">
              <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full glass-frosted border border-red-500/30 text-red-400 text-xs font-semibold shadow-inner">
                <Sparkles className="w-3.5 h-3.5 animate-pulse text-red-500" />
                <span>Largest SaaS Provider in Ethiopia</span>
                <span className="w-1 h-1 rounded-full bg-red-400" />
                <span className="text-gray-300">RAG AI &amp; Database Ops</span>
              </div>
              
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-tight tracking-tight">
                Enterprise Database
                <span className="block mt-1 text-transparent bg-clip-text bg-gradient-to-r from-red-500 via-red-400 to-rose-300">
                  Telemetry &amp; RAG Intelligence
                </span>
              </h1>
              
              <p className="text-base sm:text-lg text-gray-300 leading-relaxed max-w-2xl font-normal">
                Unified cross-system monitoring engineered for high-availability database clusters. 
                Experience real-time telemetry across <strong className="text-white">Database</strong>, <strong className="text-white">Server Nodes</strong>, 
                and <strong className="text-white">Perimeter Security</strong> powered by Grok AI diagnostics.
              </p>

              {/* CTAs */}
              <div className="flex flex-col sm:flex-row gap-4 pt-2">
                <button
                  onClick={handleGetStarted}
                  className="px-8 py-4 rounded-xl bg-gradient-to-r from-red-600 via-red-600 to-red-700 text-white font-bold hover:from-red-500 hover:to-red-600 transform hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 shadow-[0_0_30px_rgba(227,6,19,0.4)] flex items-center justify-center space-x-2"
                >
                  <span>Launch Platform</span>
                  <ArrowRight className="w-5 h-5 ml-1" />
                </button>
                
                <a
                  href="#features"
                  className="px-8 py-4 glass-frosted text-gray-200 font-semibold rounded-xl border border-white/10 hover:border-red-500/50 hover:text-white hover:bg-white/5 transition-all duration-200 text-center flex items-center justify-center"
                >
                  Explore Architecture
                </a>
              </div>

              {/* Enterprise Stats Cards */}
              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-white/10">
                <div className="glass-frosted p-3.5 rounded-xl border border-white/5">
                  <div className="text-2xl sm:text-3xl font-black text-red-500 font-mono">99.98%</div>
                  <div className="text-xs text-gray-400 mt-1 font-medium">Platform Uptime</div>
                </div>
                <div className="glass-frosted p-3.5 rounded-xl border border-white/5">
                  <div className="text-2xl sm:text-3xl font-black text-emerald-400 font-mono">&lt; 8ms</div>
                  <div className="text-xs text-gray-400 mt-1 font-medium">Query Latency</div>
                </div>
                <div className="glass-frosted p-3.5 rounded-xl border border-white/5">
                  <div className="text-2xl sm:text-3xl font-black text-white font-mono">3-in-1</div>
                  <div className="text-xs text-gray-400 mt-1 font-medium">Unified Synergy</div>
                </div>
              </div>
            </div>

            {/* Right Column: Transparent Animated Mockup Card */}
            <div className="lg:col-span-5 relative animate-float">
              {/* Decorative Red Halo */}
              <div className="absolute -inset-1 bg-gradient-to-r from-red-600 to-rose-600 rounded-3xl blur-xl opacity-30 group-hover:opacity-100 transition duration-1000 animate-pulse-glow" />

              <div className="relative glass-frosted-card rounded-2xl p-6 border border-white/15 shadow-2xl backdrop-blur-2xl">
                {/* Window Controls */}
                <div className="flex items-center justify-between pb-4 border-b border-white/10">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                    <span className="text-xs font-mono text-gray-400 ml-2">redcloud-telemetry.live</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
                    REALTIME WS
                  </span>
                </div>

                {/* Animated Simulated Telemetry */}
                <div className="mt-5 space-y-4 font-mono text-xs">
                  {/* Database Node */}
                  <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400">
                        <Database className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-bold text-white text-xs">Database Cluster</div>
                        <div className="text-[10px] text-gray-400">Buffer Hit 99.8% • 1,420 QPS</div>
                      </div>
                    </div>
                    <span className="text-emerald-400 font-bold text-[11px]">OPTIMAL</span>
                  </div>

                  {/* Server Cluster */}
                  <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/30 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
                        <Server className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-bold text-white text-xs">Server Infrastructure</div>
                        <div className="text-[10px] text-gray-400">28% CPU • 3 Nodes Active</div>
                      </div>
                    </div>
                    <span className="text-cyan-400 font-bold text-[11px]">ONLINE</span>
                  </div>

                  {/* Security Perimeter */}
                  <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/30 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-lg bg-purple-500/20 text-purple-400">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-bold text-white text-xs">Perimeter Defense</div>
                        <div className="text-[10px] text-gray-400">247 WAF Rules • 0 Threats</div>
                      </div>
                    </div>
                    <span className="text-purple-400 font-bold text-[11px]">GUARDED</span>
                  </div>

                  {/* Grok AI Diagnostic Stream */}
                  <div className="p-3.5 rounded-xl bg-red-950/20 border border-red-500/30">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 text-red-400">
                        <Bot className="w-4 h-4" />
                        <span className="font-bold text-xs">Grok AI Diagnostics</span>
                      </div>
                      <span className="text-[10px] text-gray-400">v1.4</span>
                    </div>
                    <p className="text-[11px] text-gray-300 leading-relaxed font-sans">
                      &quot;Tri-system synchronization validated. No latency spikes detected across PostgreSQL and vector storage.&quot;
                    </p>
                  </div>
                </div>

                {/* Floating Status Pill */}
                <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] text-gray-400">
                  <div className="flex items-center space-x-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    <span>Red Cloud ICT Network Active</span>
                  </div>
                  <span className="text-red-400 font-semibold cursor-pointer hover:underline" onClick={() => navigate('/login')}>
                    Sign in to Monitor &rarr;
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Features Section */}
      <section id="features" className="py-24 px-6 relative z-10 border-t border-white/10 bg-black/40">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16 space-y-3">
            <span className="text-xs font-bold text-red-500 uppercase tracking-widest bg-red-600/10 px-3 py-1 rounded-full border border-red-500/20">
              Enterprise Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
              Engineered for Mission-Critical Infrastructure
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto text-sm sm:text-base">
              Robust capabilities designed for Ethiopian enterprise IT, cloud infrastructure, and site reliability engineers.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-red-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-500 mb-5 group-hover:scale-110 transition-transform">
                <Database className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-red-400 transition-colors">
                Live Database Telemetry
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Stream live queries, table row metrics, buffer cache hits, and transaction locks directly without reload.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-cyan-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-5 group-hover:scale-110 transition-transform">
                <Server className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-cyan-300 transition-colors">
                Server Cluster Monitoring
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Deep node metrics: CPU load, RAM allocation, disk throughput, and service latency across all cluster nodes.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-purple-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400 mb-5 group-hover:scale-110 transition-transform">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                Perimeter Defense &amp; Audit
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Real-time intrusion detection, rate-limit enforcement, immutable audit logs, and account lockout defenses.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-red-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-500 mb-5 group-hover:scale-110 transition-transform">
                <Bot className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-red-400 transition-colors">
                Grok 3-in-1 RAG AI
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Synthesizes cross-system data to explain bottlenecks, recommend index tuning, and answer natural language queries.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-emerald-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-5 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-emerald-300 transition-colors">
                Real-Time Alert Center
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                WebSocket event pipeline for instant critical and warning alerts with acoustic priority and Telegram bridge.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 rounded-2xl glass-frosted border border-white/10 hover:border-blue-500/50 hover:bg-white/[0.04] transition-all duration-300 group">
              <div className="w-12 h-12 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-5 group-hover:scale-110 transition-transform">
                <Lock className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-300 transition-colors">
                Enterprise RBAC &amp; 2FA
              </h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                Granular superadmin and admin roles with enforced session integrity, CSRF tokens, and 24-hour enterprise persistence.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="py-20 px-6 relative z-10">
        <div className="max-w-5xl mx-auto glass-frosted-card rounded-3xl p-10 sm:p-14 border border-red-500/30 text-center relative overflow-hidden">
          <div className="absolute top-0 right-1/2 translate-x-1/2 w-96 h-96 bg-red-600/20 rounded-full blur-3xl pointer-events-none" />
          
          <div className="relative z-10 space-y-5">
            <h2 className="text-3xl sm:text-5xl font-black text-white tracking-tight">
              Ready to Monitor Your Infrastructure?
            </h2>
            <p className="text-gray-300 max-w-xl mx-auto text-base">
              Experience the power of Red Cloud ICT Solutions—the largest SaaS provider in Ethiopia.
            </p>
            <div className="pt-2">
              <button
                onClick={handleGetStarted}
                className="px-10 py-4 bg-gradient-to-r from-red-600 via-red-600 to-red-700 text-white font-bold rounded-xl hover:from-red-500 hover:to-red-600 transform hover:scale-105 active:scale-95 transition-all shadow-[0_0_35px_rgba(227,6,19,0.5)] inline-flex items-center space-x-2"
              >
                <span>Sign In to Dashboard</span>
                <ArrowRight className="w-5 h-5 ml-1" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Transparent Glass Footer */}
      <footer className="py-12 px-6 border-t border-white/10 bg-black/60 relative z-10 text-gray-400">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <Logo size={26} className="flex-shrink-0" />
            <div className="flex flex-col">
              <div className="flex items-center space-x-1">
                <span className="font-black text-red-600 text-base">RED</span>
                <span className="font-extrabold text-white text-base">Cloud</span>
              </div>
              <span className="text-[9px] text-gray-400 font-semibold uppercase tracking-wider">ICT Solutions • Ethiopia</span>
            </div>
          </div>

          <p className="text-xs text-gray-400 text-center md:text-left">
            &copy; {new Date().getFullYear()} Red Cloud ICT Solutions. All rights reserved. Enterprise Database RAG Platform.
          </p>

          <div className="flex items-center space-x-6 text-xs text-gray-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="/login" className="hover:text-red-400 transition-colors">Portal Login</a>
            <span className="text-emerald-400 font-mono">Status: 100% OK</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
