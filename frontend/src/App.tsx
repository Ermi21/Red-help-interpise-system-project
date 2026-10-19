import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { TelegramProvider } from './context/TelegramContext';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import DashboardLayout from './components/layout/DashboardLayout';
import DashboardOverview from './pages/Dashboard/DashboardOverview';
import DatabaseMonitoring from './pages/Dashboard/DatabaseMonitoring';
import ServerMonitoring from './pages/Dashboard/ServerMonitoring';
import SecurityMonitoring from './pages/Dashboard/SecurityMonitoring';
import Alerts from './pages/Dashboard/Alerts';
import Profile from './pages/Dashboard/Profile';
import AIAssistant from './pages/Dashboard/AIAssistant';
import AuditLog from './pages/Dashboard/AuditLog';
import Landing from './pages/Landing';

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: any }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error('React Error Boundary caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
          <div className="max-w-md w-full bg-surface border border-danger/30 rounded-2xl p-8 text-center shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-danger/10 border border-danger/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-danger text-2xl">⚠</span>
            </div>
            <h2 className="text-xl font-bold text-textPrimary mb-2">Application Error</h2>
            <p className="text-textSecondary text-sm mb-4">{this.state.error?.message || 'An unexpected error occurred.'}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-6 py-2.5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium text-sm"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function NotFound() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
      <div className="max-w-md w-full bg-surface border border-border rounded-2xl p-8 text-center shadow-2xl">
        <div className="w-20 h-20 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-6">
          <span className="text-primary font-bold text-3xl">404</span>
        </div>
        <h2 className="text-2xl font-bold text-textPrimary mb-2">Page Not Found</h2>
        <p className="text-textSecondary text-sm mb-6">The page you're looking for doesn't exist or has been moved.</p>
        <Link
          to="/dashboard"
          className="px-6 py-2.5 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors font-medium text-sm inline-block"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <TelegramProvider>
        <ThemeProvider>
          <AuthProvider>
            <BrowserRouter basename="/">
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                
                {/* Main Dashboard Layout and Routes */}
                <Route path="/dashboard" element={<DashboardLayout />}>
                  <Route index element={<DashboardOverview />} />
                  <Route path="database" element={<DatabaseMonitoring />} />
                  <Route path="server" element={<ServerMonitoring />} />
                  <Route path="security" element={<SecurityMonitoring />} />
                  <Route path="alerts" element={<Alerts />} />
                  <Route path="profile" element={<Profile />} />
                  <Route path="ai" element={<AIAssistant />} />
                  <Route path="audit" element={<AuditLog />} />
                </Route>

                {/* Direct aliases for top-level navigation */}
                <Route path="/database" element={<Navigate to="/dashboard/database" replace />} />
                <Route path="/server" element={<Navigate to="/dashboard/server" replace />} />
                <Route path="/security" element={<Navigate to="/dashboard/security" replace />} />
                <Route path="/alerts" element={<Navigate to="/dashboard/alerts" replace />} />
                <Route path="/profile" element={<Navigate to="/dashboard/profile" replace />} />
                <Route path="/ai" element={<Navigate to="/dashboard/ai" replace />} />
                <Route path="/audit" element={<Navigate to="/dashboard/audit" replace />} />

                {/* Redcloud prefixed routes for compatibility */}
                <Route path="/Redcloud" element={<Navigate to="/dashboard" replace />} />
                <Route path="/Redcloud/*" element={<Navigate to="/dashboard" replace />} />

                <Route path="*" element={<NotFound />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </ThemeProvider>
      </TelegramProvider>
    </ErrorBoundary>
  );
}

export default App;
