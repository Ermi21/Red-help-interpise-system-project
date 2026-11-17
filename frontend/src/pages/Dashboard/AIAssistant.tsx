import React, { useState } from 'react';
import { Database, Server, ShieldAlert, Sparkles, Terminal, Activity, ShieldCheck } from 'lucide-react';
import AIChatInterface from '../../components/ui/AIChatInterface';

type Domain = 'database' | 'infrastructure' | 'security';

interface DomainConfig {
  title: string;
  description: string;
  systemGreeting: string;
  themeColor: string;
  accentGradient: string;
  tag: string;
}

const domainConfig: Record<Domain, DomainConfig> = {
  database: {
    title: 'Database AI Assistant',
    description: 'Text-to-SQL, Schema Intelligence & Query Performance',
    systemGreeting:
      'Hello, Administrator. I am your Database AI Assistant. I have deep insights into query performance, schema optimization, and storage metrics. How can I assist you with your databases today?',
    themeColor: 'cyan',
    accentGradient: 'from-cyan-500 via-blue-500 to-indigo-600',
    tag: 'SQL & Schema'
  },
  infrastructure: {
    title: 'Server AI Assistant',
    description: 'SRE Infrastructure Health, Cluster Metrics & Diagnostics',
    systemGreeting:
      "Hello, Administrator. I am your Infrastructure AI Assistant. I continuously monitor server health, cluster orchestration, and resource utilization. Please detail the server metrics you'd like me to analyze.",
    themeColor: 'emerald',
    accentGradient: 'from-emerald-500 via-teal-500 to-green-600',
    tag: 'Cluster & SRE'
  },
  security: {
    title: 'Security AI Assistant',
    description: 'Real-time Threat Detection, DLP & Perimeter Audits',
    systemGreeting:
      'Hello, Administrator. I am your Security AI Assistant. I monitor intrusion attempts, analyze security logs, and detect anomalies in real time. What security concern can I help you investigate?',
    themeColor: 'rose',
    accentGradient: 'from-rose-500 via-red-500 to-amber-600',
    tag: 'Cyber & Threat'
  }
};

interface ButtonOption {
  domain: Domain;
  label: string;
  Icon: React.ElementType;
  activeClass: string;
  inactiveClass: string;
  glowClass: string;
  iconBgActive: string;
}

const domainButtons: ButtonOption[] = [
  {
    domain: 'database',
    label: 'Database AI',
    Icon: Database,
    activeClass: 'bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/25 border-cyan-400/50 ring-2 ring-cyan-400/30',
    inactiveClass: 'bg-surface/80 text-textSecondary hover:text-cyan-400 hover:bg-cyan-500/10 border-border/80 hover:border-cyan-500/40',
    glowClass: 'bg-cyan-400',
    iconBgActive: 'bg-white/20 text-white border-white/30'
  },
  {
    domain: 'infrastructure',
    label: 'Server AI',
    Icon: Server,
    activeClass: 'bg-gradient-to-r from-emerald-600 via-teal-600 to-green-600 text-white shadow-lg shadow-emerald-500/25 border-emerald-400/50 ring-2 ring-emerald-400/30',
    inactiveClass: 'bg-surface/80 text-textSecondary hover:text-emerald-400 hover:bg-emerald-500/10 border-border/80 hover:border-emerald-500/40',
    glowClass: 'bg-emerald-400',
    iconBgActive: 'bg-white/20 text-white border-white/30'
  },
  {
    domain: 'security',
    label: 'Security AI',
    Icon: ShieldAlert,
    activeClass: 'bg-gradient-to-r from-rose-600 via-red-600 to-amber-600 text-white shadow-lg shadow-rose-500/25 border-rose-400/50 ring-2 ring-rose-400/30',
    inactiveClass: 'bg-surface/80 text-textSecondary hover:text-rose-400 hover:bg-rose-500/10 border-border/80 hover:border-rose-500/40',
    glowClass: 'bg-rose-400',
    iconBgActive: 'bg-white/20 text-white border-white/30'
  }
];

export default function AIAssistant() {
  const [domain, setDomain] = useState<Domain>('database');
  const config = domainConfig[domain];

  return (
    <div className="h-full flex flex-col space-y-4 animate-fade-in">
      {/* Header Bar with Attractive Distinct Color Buttons */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-surface/40 p-3 rounded-2xl border border-border backdrop-blur-md shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-textPrimary flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary animate-pulse" />
            <span>AI Operations Assistant</span>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold border bg-primary/10 text-primary border-primary/30">
              Enterprise v2.0
            </span>
          </h1>
        </div>

        {/* 3 Distinctly Colored Action Buttons (Clean & Professional Standard) */}
        <div className="flex items-center gap-2.5 w-full lg:w-auto overflow-x-auto pb-1 lg:pb-0">
          {domainButtons.map(({ domain: d, label, Icon, activeClass, inactiveClass, glowClass, iconBgActive }) => {
            const isActive = domain === d;
            return (
              <button
                key={d}
                onClick={() => setDomain(d)}
                className={`relative group flex items-center gap-2.5 px-4 py-2.5 rounded-xl border font-semibold text-sm transition-all duration-200 text-left flex-1 lg:flex-initial shadow-sm ${
                  isActive ? activeClass : inactiveClass
                }`}
              >
                {/* Glowing Dot on Active */}
                {isActive && (
                  <span className={`absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full ${glowClass} shadow-md shadow-white animate-ping`} />
                )}

                {/* Icon Container */}
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center border transition-transform duration-200 group-hover:scale-105 ${
                    isActive ? iconBgActive : 'bg-surface border-border text-textSecondary group-hover:text-textPrimary'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>

                {/* Text */}
                <span className="text-sm font-bold tracking-tight">{label}</span>

                {/* Live Indicator Dot */}
                <span className={`w-2 h-2 rounded-full ml-auto transition-all ${isActive ? 'bg-white shadow-sm shadow-white animate-pulse' : 'bg-border/60'}`} />
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Chat Interface Container */}
      <div className="flex-1 glass-panel border border-border rounded-2xl overflow-hidden relative shadow-md">
        <AIChatInterface
          key={domain}
          domain={domain}
          title={config.title}
          description={config.description}
          systemGreeting={config.systemGreeting}
        />
      </div>
    </div>
  );
}
