import React, { createContext, useContext, useState, useEffect } from 'react';

export interface UserAccount {
  email: string;
  role: 'admin' | 'superadmin';
  password?: string;
  needsPasswordChange?: boolean;
}

export interface PasswordRequest {
  email: string;
  newPassword?: string;
  status: 'pending' | 'approved';
}

interface AuthContextType {
  isAuthenticated: boolean;
  login: (email: string, password?: string, telegramChatId?: string) => Promise<void>;
  logout: () => void;
  userEmail: string | null;
  role: 'admin' | 'superadmin' | null;
  avatar: string | null;
  updateAvatar: (base64Image: string) => Promise<void>;
  needsPasswordChange: boolean;
  setNeedsPasswordChange: (val: boolean) => void;
  passwordRequests: PasswordRequest[];
  addPasswordRequest: (email: string, newPassword?: string) => void;
  approvePasswordRequest: (email: string) => void;
  profileComplete: boolean;
  completeProfile: () => void;
  users: UserAccount[];
  addUser: (email: string, role: 'admin' | 'superadmin', pass: string) => Promise<void>;
  updateUserPassword: (email: string, newPass: string) => Promise<void>;
  loginTime: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const safeFetchJson = async (url: string, options: RequestInit) => {
  try {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    const text = await response.text();

    if (!text || !response.ok || !contentType.includes('application/json')) {
      return null;
    }

    return JSON.parse(text);
  } catch (err) {
    return null;
  }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Load initial values from localStorage if available and not expired
  const getInitialState = () => {
    const isAuth = localStorage.getItem('auth_isAuthenticated') === 'true';
    const timestampStr = localStorage.getItem('auth_timestamp');
    const loginTimeStr = localStorage.getItem('auth_loginTime') || new Date().toISOString();
    if (!isAuth || !timestampStr) {
      return { isAuth: false, email: null, role: null, avatar: null, complete: false, change: false, loginTime: null };
    }
    const timestamp = parseInt(timestampStr, 10);
    const now = Date.now();
    const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours full enterprise session

    if (now - timestamp > SESSION_DURATION) {
      // Session expired
      localStorage.clear();
      return { isAuth: false, email: null, role: null, avatar: null, complete: false, change: false, loginTime: null };
    }

    const email = localStorage.getItem('auth_userEmail');
    const emailClean = (email || '').toLowerCase().trim();
    const storedAvatar = localStorage.getItem('auth_avatar') ||
                         (emailClean ? localStorage.getItem(`user_avatar_${emailClean}`) : null) ||
                         (emailClean.includes('superadmin') || emailClean.includes('ermigech') ? localStorage.getItem('user_avatar_superadmin') : null) ||
                         localStorage.getItem('app_persistent_avatar');

    // Refresh timestamp
    localStorage.setItem('auth_timestamp', now.toString());
    return {
      isAuth: true,
      email: email,
      role: localStorage.getItem('auth_role') as 'admin' | 'superadmin',
      avatar: storedAvatar,
      complete: localStorage.getItem('auth_profileComplete') === 'true',
      change: localStorage.getItem('auth_needsPasswordChange') === 'true',
      loginTime: loginTimeStr
    };
  };

  const initialState = getInitialState();

  const [isAuthenticated, setIsAuthenticated] = useState(initialState.isAuth);
  const [userEmail, setUserEmail] = useState<string | null>(initialState.email);
  const [role, setRole] = useState<'admin' | 'superadmin' | null>(initialState.role);
  const [avatar, setAvatar] = useState<string | null>(initialState.avatar);
  const [needsPasswordChange, setNeedsPasswordChange] = useState(initialState.change);
  const [passwordRequests, setPasswordRequests] = useState<PasswordRequest[]>([]);
  const [profileComplete, setProfileComplete] = useState<boolean>(initialState.complete);
  const [loginTime, setLoginTime] = useState<string | null>(initialState.loginTime);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);

  // Monitor user activity and handle 24-hour session expiry
  useEffect(() => {
    if (!isAuthenticated) return;

    const SESSION_DURATION = 24 * 60 * 60 * 1000; // 24 hours

    // Check every 30 seconds if session has expired
    const interval = setInterval(() => {
      const timestampStr = localStorage.getItem('auth_timestamp');
      if (timestampStr) {
        const timestamp = parseInt(timestampStr, 10);
        const now = Date.now();
        if (now - timestamp > SESSION_DURATION) {
          logout();
        }
      } else {
        localStorage.setItem('auth_timestamp', Date.now().toString());
      }
    }, 30000);

    // Refresh the session timer whenever the user interacts with the app
    const handleActivity = () => {
      localStorage.setItem('auth_timestamp', Date.now().toString());
    };

    window.addEventListener('click', handleActivity, { passive: true });
    window.addEventListener('keydown', handleActivity, { passive: true });
    window.addEventListener('mousemove', handleActivity, { passive: true });
    window.addEventListener('focus', handleActivity);
    document.addEventListener('visibilitychange', handleActivity);

    return () => {
      clearInterval(interval);
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('focus', handleActivity);
      document.removeEventListener('visibilitychange', handleActivity);
    };
  }, [isAuthenticated]);

  // Check URL or sessionStorage for telegram_chat_id and register it if authenticated
  useEffect(() => {
    // If not authenticated yet but parameter is in URL, cache it immediately so it survives redirects!
    const urlParams = new URLSearchParams(window.location.search);
    const urlChatId = urlParams.get('telegram_chat_id');
    if (urlChatId && urlChatId !== 'undefined' && urlChatId !== 'null') {
      sessionStorage.setItem('telegram_chat_id', urlChatId);
    }

    if (isAuthenticated && userEmail) {
      const telegramChatId = urlChatId || sessionStorage.getItem('telegram_chat_id');
      if (telegramChatId && telegramChatId !== 'undefined' && telegramChatId !== 'null') {
        const chatHistoryUrl = import.meta.env.VITE_N8N_CHAT_HISTORY_URL || 'http://localhost:5678/webhook/chat-history';
        fetch(chatHistoryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: 'register_telegram',
            email: userEmail,
            telegram_chat_id: telegramChatId
          })
        })
          .then(res => {
            if (res.ok) {
              console.log("Registered Telegram Chat ID successfully!");
              sessionStorage.removeItem('telegram_chat_id');
              const newUrl = window.location.pathname;
              window.history.replaceState({}, document.title, newUrl);
            }
          })
          .catch(e => console.warn("Failed to register Telegram Chat ID:", e));
      }
    }
  }, [isAuthenticated, userEmail]);

  useEffect(() => {
    // Fetch users from n8n on mount (strictly in-memory, no localStorage checks)
    const fetchUsers = async () => {
      try {
        const authUrl = import.meta.env.VITE_N8N_AUTH_URL || 'http://localhost:5678/webhook/erp-auth';
        const data = await safeFetchJson(authUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ operation: 'list_users' })
        });
        if (Array.isArray(data)) {
          const fetchedUsers = data.map(u => ({
            email: u.email || u.user_email,
            role: u.role || 'admin',
            needsPasswordChange: u.needs_password_change || false
          }));
          if (fetchedUsers.length > 0) {
            setUsers(prev => {
              const combined = [...prev, ...fetchedUsers];
              return combined.reduce((acc: UserAccount[], user) => {
                const existingIdx = acc.findIndex(u => u.email.toLowerCase() === user.email.toLowerCase());
                if (existingIdx >= 0) {
                  acc[existingIdx] = user;
                } else {
                  acc.push(user);
                }
                return acc;
              }, []);
            });
          }
        }
      } catch (e) {
        console.warn('Failed to fetch users from n8n', e);
      }
    };
    fetchUsers();
    setLoading(false);
  }, []);

  const fetchAvatarFromBackend = async (email: string): Promise<string | null> => {
    const clean = (email || '').toLowerCase().trim();
    if (!clean) return null;
    const endpoints = [
      `/api/v1/auth/avatar?email=${encodeURIComponent(clean)}`,
      `https://red-help-interpise-system-project.onrender.com/api/v1/auth/avatar?email=${encodeURIComponent(clean)}`
    ];
    for (const url of endpoints) {
      try {
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data && data.avatar) return data.avatar;
        }
      } catch (e) {
        // Continue to fallback
      }
    }
    return null;
  };

  const syncAvatarToBackend = async (email: string, base64Image: string) => {
    const clean = (email || '').toLowerCase().trim();
    const endpoints = [
      '/api/v1/auth/avatar',
      'https://red-help-interpise-system-project.onrender.com/api/v1/auth/avatar'
    ];
    for (const url of endpoints) {
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: clean, avatar: base64Image })
        });
        if (res.ok) break;
      } catch (e) {
        // Continue to fallback
      }
    }
  };

  // Restore avatar from backend on mount if user is already logged in
  useEffect(() => {
    if (isAuthenticated && userEmail) {
      fetchAvatarFromBackend(userEmail).then(remoteAvatar => {
        if (remoteAvatar) {
          setAvatar(remoteAvatar);
          localStorage.setItem('auth_avatar', remoteAvatar);
          localStorage.setItem('app_persistent_avatar', remoteAvatar);
          localStorage.setItem(`user_avatar_${userEmail.toLowerCase().trim()}`, remoteAvatar);
          localStorage.setItem('user_avatar_superadmin', remoteAvatar);
          window.dispatchEvent(new Event('auth_avatar_changed'));
        }
      });
    }
  }, [isAuthenticated, userEmail]);

  const login = async (email: string, password?: string, telegramChatId?: string) => {
    const emailNorm = (email || '').toLowerCase().trim();
    let userRole: 'admin' | 'superadmin' = (
      emailNorm === 'ermigech119@gmail.com' ||
      emailNorm === 'ermigech119' ||
      emailNorm === 'superadmin@company.com' ||
      emailNorm === 'superadmin@gmail.com' ||
      emailNorm === 'superadmin'
    ) ? 'superadmin' : 'admin';
    let needsChange = false;
    let authSuccess = false;

    // 1. Authenticate against our FastAPI backend with cloud cold-start resilience
    const endpoints = [
      '/api/v1/auth/login',
      'https://red-help-interpise-system-project.onrender.com/api/v1/auth/login'
    ];

    let lastError: any = null;
    let isCredentialError = false;

    for (const endpoint of endpoints) {
      if (authSuccess) break;
      try {
        const controller = new AbortController();
        // Render free-tier cold starts can take 25-40s; allow 45s before aborting
        const timer = setTimeout(() => controller.abort(), 45000);
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: email, password: password || '' }),
          signal: controller.signal
        });
        clearTimeout(timer);

        if (res.ok) {
          const apiData = await res.json();
          userRole = (
            emailNorm === 'ermigech119@gmail.com' ||
            emailNorm === 'ermigech119' ||
            emailNorm === 'superadmin@company.com' ||
            emailNorm === 'superadmin@gmail.com' ||
            apiData.user?.role === 'superadmin'
          ) ? 'superadmin' : (apiData.user?.role || 'admin');
          authSuccess = true;
          if (apiData.access_token) {
            localStorage.setItem('access_token', apiData.access_token);
            localStorage.setItem('auth_token', apiData.access_token);
            localStorage.setItem('authToken', apiData.access_token);
          }
          break;
        } else if (res.status === 401 || res.status === 400) {
          isCredentialError = true;
          const errJson = await res.json().catch(() => ({}));
          throw new Error(errJson.message || 'Invalid username or password.');
        } else if (res.status >= 500) {
          lastError = new Error('Cloud backend server is warming up. Please wait a moment and try again.');
        }
      } catch (backendErr: any) {
        if (isCredentialError || (backendErr?.message && (backendErr.message.includes('Invalid') || backendErr.message.includes('password')))) {
          throw backendErr;
        }
        lastError = backendErr;
        console.warn(`FastAPI backend attempt at ${endpoint} notice:`, backendErr);
      }
    }

    // 2. Try n8n backend PostgreSQL Auth Webhook if available
    if (!authSuccess && !isCredentialError) {
      try {
        const authUrl = import.meta.env.VITE_N8N_AUTH_URL;
        if (authUrl) {
          const data = await safeFetchJson(authUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              operation: 'login',
              body: { email, password }
            })
          });
          if (data && data.success && data.user) {
            userRole = data.user.role || userRole;
            needsChange = !!data.user.needs_password_change;
            if (data.user.avatar) {
              setAvatar(data.user.avatar);
              localStorage.setItem('auth_avatar', data.user.avatar);
            }
            authSuccess = true;
          }
        }
      } catch (err: any) {
        console.warn("n8n authentication unavailable:", err);
      }
    }

    // 3. Resilient enterprise admin fallback when cloud backend is waking up (cold start) or DB unseeded
    const isSuperadminCreds = (
      (emailNorm === 'ermigech119@gmail.com' ||
       emailNorm === 'ermigech119' ||
       emailNorm === 'superadmin@company.com' ||
       emailNorm === 'superadmin@gmail.com' ||
       emailNorm === 'superadmin' ||
       emailNorm === 'admin' ||
       emailNorm === 'admin@company.com') &&
      (password === 'Ermi1926@#' || password === 'admin123' || password === 'admin')
    );

    if (!authSuccess && isSuperadminCreds) {
      userRole = 'superadmin';
      authSuccess = true;
      if (!localStorage.getItem('access_token')) {
        const fallbackToken = 'enterprise-admin-token-' + Date.now();
        localStorage.setItem('access_token', fallbackToken);
        localStorage.setItem('auth_token', fallbackToken);
        localStorage.setItem('authToken', fallbackToken);
      }
    }

    if (!authSuccess) {
      if (isCredentialError) {
        throw new Error('Invalid email or password.');
      }
      if (lastError?.name === 'AbortError' || lastError?.message?.includes('Failed to fetch') || lastError?.message?.includes('NetworkError') || lastError?.message?.includes('warming up')) {
        const netErr: any = new Error('Connecting to cloud server... The backend is waking up (cold start). Please click Sign In again.');
        netErr.isColdStart = true;
        throw netErr;
      }
      throw new Error('Invalid email or password.');
    }

    const nowLoginTime = new Date().toISOString();
    const emailClean = emailNorm;
    let savedAvatar = localStorage.getItem(`user_avatar_${emailClean}`) ||
                      (emailClean.includes('superadmin') || emailClean.includes('ermigech') ? localStorage.getItem('user_avatar_superadmin') : null) ||
                      localStorage.getItem('auth_avatar') ||
                      localStorage.getItem('app_persistent_avatar');

    // Asynchronously verify with backend database for newest avatar
    try {
      const remoteAvatar = await fetchAvatarFromBackend(emailClean);
      if (remoteAvatar) {
        savedAvatar = remoteAvatar;
      }
    } catch (e) {}

    if (savedAvatar) {
      setAvatar(savedAvatar);
      localStorage.setItem('auth_avatar', savedAvatar);
      localStorage.setItem('app_persistent_avatar', savedAvatar);
      localStorage.setItem(`user_avatar_${emailClean}`, savedAvatar);
      localStorage.setItem('user_avatar_superadmin', savedAvatar);
      window.dispatchEvent(new Event('auth_avatar_changed'));
    }
    setIsAuthenticated(true);
    setUserEmail(email);
    setRole(userRole);
    setNeedsPasswordChange(needsChange);
    setProfileComplete(false); // default profileComplete to false in-memory
    setLoginTime(nowLoginTime);

    // Store in localStorage
    localStorage.setItem('auth_isAuthenticated', 'true');
    localStorage.setItem('auth_userEmail', email);
    localStorage.setItem('auth_role', userRole);
    localStorage.setItem('auth_profileComplete', 'false');
    localStorage.setItem('auth_needsPasswordChange', needsChange ? 'true' : 'false');
    localStorage.setItem('auth_timestamp', Date.now().toString());
    localStorage.setItem('auth_loginTime', nowLoginTime);

    if (telegramChatId && telegramChatId !== 'undefined' && telegramChatId !== 'null') {
      const chatHistoryUrl = import.meta.env.VITE_N8N_CHAT_HISTORY_URL || 'http://localhost:5678/webhook/chat-history';
      fetch(chatHistoryUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation: 'register_telegram',
          email: email,
          telegram_chat_id: telegramChatId
        })
      })
        .then(res => {
          if (res.ok) {
            console.log("Registered Telegram Chat ID successfully on login!");
          }
        })
        .catch(e => console.warn("Failed to register Telegram Chat ID on login:", e));
    }
  };

  const updateAvatar = async (base64Image: string) => {
    setAvatar(base64Image);
    const activeEmail = (userEmail || localStorage.getItem('auth_userEmail') || 'ermigech119@gmail.com').toLowerCase().trim();
    
    // 1. Immediately save across all persistent browser storage keys
    localStorage.setItem('auth_avatar', base64Image);
    localStorage.setItem('app_persistent_avatar', base64Image);
    localStorage.setItem(`user_avatar_${activeEmail}`, base64Image);
    localStorage.setItem('user_avatar_superadmin', base64Image);
    localStorage.setItem('user_avatar_ermigech119@gmail.com', base64Image);
    window.dispatchEvent(new Event('auth_avatar_changed'));

    // 2. Permanently persist to backend PostgreSQL/SQLite database
    await syncAvatarToBackend(activeEmail, base64Image);

    // 3. Sync to optional n8n webhook if configured
    if (activeEmail) {
      try {
        const authUrl = import.meta.env.VITE_N8N_AUTH_URL || 'http://localhost:5678/webhook/erp-auth';
        await fetch(authUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            operation: 'update_avatar',
            body: { email: activeEmail, avatar: base64Image }
          })
        });
      } catch (err) {
        console.warn("Failed to sync avatar to backend", err);
      }
    }
  };

  const completeProfile = () => {
    setProfileComplete(true);
    localStorage.setItem('auth_profileComplete', 'true');
  };

  const logout = () => {
    localStorage.removeItem('auth_isAuthenticated');
    localStorage.removeItem('auth_userEmail');
    localStorage.removeItem('auth_role');
    // Note: Do NOT remove user_avatar_* or app_persistent_avatar so user's uploaded profile photo is preserved across re-logins!
    localStorage.removeItem('auth_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('authToken');
    localStorage.removeItem('auth_timestamp');
    localStorage.removeItem('auth_loginTime');
    localStorage.removeItem('auth_profileComplete');
    localStorage.removeItem('auth_needsPasswordChange');

    setIsAuthenticated(false);
    setUserEmail(null);
    setRole(null);
    setAvatar(null);
    setProfileComplete(false);
    setNeedsPasswordChange(false);
    setLoginTime(null);
  };

  const addUser = async (email: string, role: 'admin' | 'superadmin', pass: string) => {
    try {
      const authUrl = import.meta.env.VITE_N8N_AUTH_URL || 'http://localhost:5678/webhook/erp-auth';
      await fetch(authUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation: 'create_user', email, role, password: pass })
      });
    } catch (err) {
      console.warn("n8n user creation webhook unreachable", err);
    }

    let newUsers: UserAccount[];
    const existingIndex = users.findIndex(u => u.email.toLowerCase() === email.toLowerCase());

    if (existingIndex >= 0) {
      newUsers = [...users];
      newUsers[existingIndex] = { ...newUsers[existingIndex], role, password: pass, needsPasswordChange: true };
    } else {
      newUsers = [...users, { email, role, password: pass, needsPasswordChange: true }];
    }

    setUsers(newUsers);
  };

  const updateUserPassword = async (email: string, newPass: string) => {
    try {
      const authUrl = import.meta.env.VITE_N8N_AUTH_URL || 'http://localhost:5678/webhook/erp-auth';
      await fetch(authUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          operation: 'update_password',
          body: { email, password: newPass }
        })
      });
    } catch (err) {
      console.warn("n8n update_password webhook unreachable", err);
    }

    const newUsers = users.map(u =>
      u.email === email ? { ...u, password: newPass, needsPasswordChange: false } : u
    );
    setUsers(newUsers);
    if (userEmail === email) {
      setNeedsPasswordChange(false);
    }
  };

  const addPasswordRequest = (email: string, newPassword?: string) => {
    const newRequests = [...passwordRequests.filter(r => r.email !== email), { email, newPassword, status: 'pending' as const }];
    setPasswordRequests(newRequests);
  };

  const approvePasswordRequest = (email: string) => {
    const request = passwordRequests.find(r => r.email === email);
    if (request && request.newPassword) {
      updateUserPassword(email, request.newPassword);
    }
    const newRequests = passwordRequests.map(r => r.email === email ? { ...r, status: 'approved' as const } : r);
    setPasswordRequests(newRequests);

    // Auto cleanup after a minute in memory
    setTimeout(() => {
      setPasswordRequests(prev => prev.filter(r => r.email !== email));
    }, 60000);
  };

  if (loading) {
    return <div className="min-h-screen bg-background flex items-center justify-center text-textPrimary">Loading...</div>;
  }

  return (
    <AuthContext.Provider value={{
      isAuthenticated, login, logout, userEmail, role, avatar, updateAvatar,
      needsPasswordChange, setNeedsPasswordChange,
      passwordRequests, addPasswordRequest, approvePasswordRequest,
      profileComplete, completeProfile,
      users, addUser, updateUserPassword,
      loginTime
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
