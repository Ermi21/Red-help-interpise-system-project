import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { Eye, EyeOff, AlertCircle, Loader2, ArrowLeft, ShieldCheck, Sparkles, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/ui/Logo';

// Rate limiting configuration
const MAX_ATTEMPTS = 5;
const LOCKOUT_DURATION = 15 * 60 * 1000; // 15 minutes in milliseconds
const RATE_LIMIT_WINDOW = 5 * 60 * 1000; // 5 minutes in milliseconds

interface LoginAttempt {
  count: number;
  firstAttempt: number;
  lockedUntil?: number;
}

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isLocked, setIsLocked] = useState(false);
  const [lockoutTimeRemaining, setLockoutTimeRemaining] = useState(0);

  // Check rate limiting and lockout status
  useEffect(() => {
    checkLockoutStatus();
    const interval = setInterval(checkLockoutStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  const getLoginAttempts = (): LoginAttempt => {
    const stored = localStorage.getItem('loginAttempts');
    if (!stored) return { count: 0, firstAttempt: Date.now() };
    
    try {
      return JSON.parse(stored);
    } catch {
      return { count: 0, firstAttempt: Date.now() };
    }
  };

  const updateLoginAttempts = (attempts: LoginAttempt) => {
    localStorage.setItem('loginAttempts', JSON.stringify(attempts));
  };

  const checkLockoutStatus = () => {
    const attempts = getLoginAttempts();
    
    if (attempts.lockedUntil && Date.now() < attempts.lockedUntil) {
      setIsLocked(true);
      setLockoutTimeRemaining(Math.ceil((attempts.lockedUntil - Date.now()) / 1000));
    } else if (attempts.lockedUntil && Date.now() >= attempts.lockedUntil) {
      // Lockout expired, reset attempts
      updateLoginAttempts({ count: 0, firstAttempt: Date.now() });
      setIsLocked(false);
      setLockoutTimeRemaining(0);
    } else {
      setIsLocked(false);
      setLockoutTimeRemaining(0);
    }
  };

  const recordFailedAttempt = () => {
    const attempts = getLoginAttempts();
    const now = Date.now();
    
    // Reset counter if outside rate limit window
    if (now - attempts.firstAttempt > RATE_LIMIT_WINDOW) {
      updateLoginAttempts({ count: 1, firstAttempt: now });
      return;
    }
    
    // Increment counter
    const newCount = attempts.count + 1;
    
    // Lock account if max attempts reached
    if (newCount >= MAX_ATTEMPTS) {
      const lockedUntil = now + LOCKOUT_DURATION;
      updateLoginAttempts({
        ...attempts,
        count: newCount,
        lockedUntil
      });
      setIsLocked(true);
      setError(`Too many failed attempts. Account locked for 15 minutes.`);
    } else {
      updateLoginAttempts({
        ...attempts,
        count: newCount
      });
      setError(`Invalid credentials. ${MAX_ATTEMPTS - newCount} attempts remaining.`);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    // Check if account is locked
    if (isLocked) {
      setError(`Account locked. Please wait ${formatTime(lockoutTimeRemaining)}.`);
      return;
    }

    // Basic validation
    if (!formData.username || !formData.password) {
      setError('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      await login(formData.username.trim(), formData.password);

      // Clear failed attempts on successful login
      updateLoginAttempts({ count: 0, firstAttempt: Date.now() });

      // Save user object and tokens in storage
      const token = localStorage.getItem('access_token') || localStorage.getItem('authToken') || '';
      const userEmail = formData.username.trim();
      const userRole = (userEmail === 'superadmin@company.com' || userEmail === 'admin') ? 'superadmin' : 'admin';
      const userObj = {
        username: userEmail.split('@')[0],
        email: userEmail.includes('@') ? userEmail : '',
        role: userRole
      };
      
      localStorage.setItem('user', JSON.stringify(userObj));
      if (token) {
        localStorage.setItem('authToken', token);
        localStorage.setItem('auth_token', token);
        localStorage.setItem('access_token', token);
      }

      // Navigate to dashboard
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Login error:', err);
      recordFailedAttempt();
      setError(err?.message || 'Invalid username or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen flex bg-gradient-to-br from-[#1a1e27] via-[#141720] to-[#0e1117] text-white selection:bg-red-600 selection:text-white relative overflow-hidden">
      {/* Dynamic Ambient Background Glow */}
      <div className="absolute top-1/4 -left-20 w-[500px] h-[500px] bg-red-600/15 rounded-full blur-[140px] pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-1/4 -right-20 w-[500px] h-[500px] bg-red-700/10 rounded-full blur-[160px] pointer-events-none animate-float-slow" />

      {/* Left Side: Official Promotional Banner Image with Transparent Gradient */}
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden bg-black">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-black/30 to-[#141720] z-10" />
        <div className="absolute inset-0 bg-red-950/15 mix-blend-multiply z-10 pointer-events-none" />
        
        <img 
          src="/assets/brand/login-banner.png"
          alt="Red Cloud ICT Solutions Ethiopian Banner" 
          className="w-full h-full object-cover scale-105 hover:scale-100 transition-transform duration-1000 ease-out"
          onError={(e) => {
            (e.target as HTMLImageElement).src = '/login-banner.png';
          }}
        />

        {/* Floating Ethiopia SaaS Badge */}
        <div className="absolute top-8 left-8 z-20">
          <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-slate-900/80 border border-red-500/40 text-white text-xs font-semibold backdrop-blur-xl shadow-xl">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span>Largest SaaS Provider in Ethiopia</span>
          </div>
        </div>

        {/* Bottom Hero Overlay */}
        <div className="absolute inset-0 z-20 flex flex-col justify-end p-12 text-white bg-gradient-to-t from-black via-black/40 to-transparent">
          <div className="flex items-center space-x-2 text-red-500 font-bold text-xs uppercase tracking-widest mb-1.5">
            <Sparkles className="w-4 h-4" />
            <span>High-Availability Cloud Solutions</span>
          </div>
          <h2 className="text-3xl lg:text-4xl font-black tracking-tight leading-tight">
            RED CLOUD ICT SOLUTIONS
          </h2>
          <p className="text-base font-semibold text-red-400 mt-1">
            Enterprise Database Operations &amp; RAG Intelligence
          </p>
          <p className="text-xs text-gray-300 mt-3 max-w-lg leading-relaxed font-light">
            Empowering Ethiopian enterprises with real-time database observability, automated failover defense, 
            and contextual conversational analytics.
          </p>
        </div>
      </div>

      {/* Right Side: Minimized Darkness Luminous Glass Login Panel */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-10 relative z-20 bg-gradient-to-br from-[#2a3243]/90 via-[#212735]/95 to-[#1b202c]/95">
        {/* Subtle illuminated ambient spotlights */}
        <div className="absolute top-10 right-10 w-72 h-72 bg-red-500/10 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="w-full max-w-md animate-fade-in relative z-10">
          {/* Back Button */}
          <button
            onClick={() => navigate('/')}
            className="mb-6 flex items-center text-slate-200 hover:text-white transition-colors group text-sm font-semibold"
          >
            <ArrowLeft className="w-4 h-4 mr-2 transform group-hover:-translate-x-1 transition-transform text-red-500" />
            Back to Home
          </button>

          {/* Luminous Frosted Glass Login Card with Minimized Darkness */}
          <div className="bg-slate-800/85 border border-slate-600/70 rounded-3xl p-8 sm:p-10 shadow-[0_25px_60px_rgba(0,0,0,0.35)] backdrop-blur-2xl relative overflow-hidden ring-1 ring-white/15">
            {/* Subtle top edge crimson glow */}
            <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-red-500 to-transparent shadow-[0_0_12px_rgba(227,6,19,0.8)]" />

            {/* Header Brand */}
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">
                <div className="p-3 rounded-2xl bg-white/15 border border-white/25 shadow-lg inline-flex items-center justify-center backdrop-blur-md">
                  <Logo size={36} className="animate-float" />
                </div>
              </div>
              
              <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight drop-shadow-sm">
                Welcome back
              </h2>
              <p className="text-xs sm:text-sm text-slate-200 mt-1 font-medium">
                Sign in to <span className="text-red-400 font-bold">Red Cloud</span> Platform
              </p>
            </div>

            {/* Error Message Pill */}
            {error && (
              <div 
                className="mb-6 p-4 rounded-xl bg-red-950/60 border border-red-500/50 text-red-200 text-xs sm:text-sm flex items-start gap-3 backdrop-blur-md animate-slide-up shadow-lg"
                role="alert"
                aria-live="polite"
              >
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div>{error}</div>
                  {isLocked && lockoutTimeRemaining > 0 && (
                    <div className="mt-1.5 font-bold font-mono text-red-300">
                      Lockout expires in: {formatTime(lockoutTimeRemaining)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Username/Email */}
              <div>
                <label 
                  htmlFor="username" 
                  className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2"
                >
                  Email or Username
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="username"
                    name="username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-700/60 border border-slate-500/60 hover:border-slate-400 rounded-xl text-white placeholder-slate-400 text-sm focus:border-red-500 focus:bg-slate-700/90 focus:ring-2 focus:ring-red-500/30 transition-all outline-none disabled:opacity-50"
                    placeholder="superadmin@company.com"
                    disabled={isLoading || isLocked}
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label 
                  htmlFor="password" 
                  className="block text-xs font-semibold text-slate-200 uppercase tracking-wider mb-2"
                >
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-700/60 border border-slate-500/60 hover:border-slate-400 rounded-xl text-white placeholder-slate-400 text-sm focus:border-red-500 focus:bg-slate-700/90 focus:ring-2 focus:ring-red-500/30 transition-all outline-none pr-12 disabled:opacity-50"
                    placeholder="••••••••••••"
                    disabled={isLoading || isLocked}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors focus:outline-none"
                    disabled={isLoading || isLocked}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Remember Me & Help */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center cursor-pointer select-none text-slate-300 hover:text-white">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-750 border-slate-600 text-red-600 focus:ring-red-500 cursor-pointer"
                    disabled={isLoading || isLocked}
                  />
                  <span className="ml-2 font-medium">Keep session active (24h)</span>
                </label>
                <a 
                  href="/forgot-password" 
                  className="text-red-400 hover:text-red-300 font-semibold transition-colors"
                  tabIndex={isLoading || isLocked ? -1 : 0}
                >
                  Forgot password?
                </a>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isLoading || isLocked || !formData.username || !formData.password}
                className="w-full py-3.5 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-red-600 via-red-600 to-red-700 hover:from-red-500 hover:to-red-600 shadow-[0_4px_20px_rgba(227,6,19,0.35)] hover:shadow-[0_6px_28px_rgba(227,6,19,0.55)] transform hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Authenticating Credentials...</span>
                  </>
                ) : isLocked ? (
                  <span>Account Locked (Exceeded Limits)</span>
                ) : (
                  <>
                    <Lock className="w-4 h-4" />
                    <span>Sign In to Platform</span>
                  </>
                )}
              </button>
            </form>

            {/* Footer Notice */}
            <div className="mt-8 pt-5 border-t border-slate-800 text-center text-xs text-slate-400 flex items-center justify-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>TLS 1.3 • Secured by Red Cloud ICT Defense</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
