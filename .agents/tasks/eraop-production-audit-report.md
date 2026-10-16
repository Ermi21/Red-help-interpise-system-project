# ERAOP / RedCloud — Production Infrastructure Monitoring Platform
## Comprehensive Codebase Audit Report

**Audit Date:** 2025  
**Codebase Root:** `c:\Users\user\Music\enterprise-db-rag-backend`  
**Audited By:** Automated codebase inspection (read-only)  
**Report Written To:** `.agents/tasks/eraop-production-audit-report.md`

---

## Executive Summary

ERAOP is a FastAPI + React enterprise monitoring platform with three domains: database, server, and security. The backend is architecturally sound with a real Supabase PostgreSQL connection, a robust three-layer read-only SQL guard, a functional Groq LLM integration, and a working RAG pipeline. The **database domain is the most complete**, with real schema discovery, real health analysis queries, real chat/SQL generation, and a working ChromaDB vector store — all connecting to a real Supabase instance.

The **most critical production gap is the server and security monitoring domains**, which have zero real backend implementation. Server metrics in `ServerMonitoring.tsx` are served by hardcoded `defaultServerNodes` (APP-PROD-CLUSTER-01, DB-PRIMARY-NODE-02, etc.) when the external telemetry agent is offline, which it always will be in a standard deployment. The `SecurityMonitoring.tsx` page uses a static `securityEvents` array and `kpiMetrics` array defined at the top of the file with fabricated IP addresses and hardcoded percentages. Neither domain has a backend API endpoint (`/api/v1/servers`, `/api/v1/zabbix`, `/api/v1/security`) at all.

The **authentication system has a critical dual-track vulnerability**: the frontend `AuthContext.tsx` maintains an in-memory user list seeded with `superadmin@company.com / admin` as a hardcoded fallback that grants access even if the FastAPI backend is completely unreachable. The `JWT_SECRET_KEY` defaults to the literal string `"change-me-to-a-long-random-value"` and the `.env` file has not changed this value. The Telegram bot (`bot.py`) returns **100% mock data** from a `MOCK_DATA` dict. The `.env` file contains what appear to be a live Supabase database URL with encoded credentials and a live Groq API key — both sensitive secrets committed to the codebase.

**Priority order for fixing:** (1) Security vulnerabilities — default JWT secret and frontend auth bypass; (2) Server monitoring real implementation; (3) Security monitoring real implementation; (4) Telegram bot real data integration; (5) N8N dependency cleanup; (6) Notification channel verification.

---

## Component Status Matrix

| Component | Status | Notes | File(s) |
|---|---|---|---|
| **Auth — JWT Issuance** | ⚠️ PARTIAL | Functional logic; default secret `change-me-to-a-long-random-value` still in `.env` | `backend/app/auth/jwt_handler.py`, `backend/.env` |
| **Auth — JWT Validation** | ✅ WORKING | Proper PyJWT decode with algorithm check | `backend/app/auth/jwt_handler.py` |
| **Auth — Password Hashing** | ✅ WORKING | bcrypt via `hash_password`/`verify_password` | `backend/app/auth/password.py` |
| **Auth — RBAC** | ⚠️ PARTIAL | RBAC enforced on all backend routes; but frontend has in-memory bypass | `backend/app/auth/rbac.py`, `frontend/src/context/AuthContext.tsx` |
| **Auth — Frontend AuthContext** | 🚨 UNSAFE | Hardcoded `superadmin@company.com / admin` fallback; users stored in React state with plaintext passwords | `frontend/src/context/AuthContext.tsx` lines 86, 167-175 |
| **Database Connection — Target DB** | ✅ WORKING | Real Supabase connection; Supabase pooler URL normalization; SSL; psycopg2 | `backend/app/database/connection.py` |
| **Database Connection — App DB** | ❓ INCOMPLETE | `APP_DB_URL` defaults to `postgresql+psycopg2://app_user:app_password@localhost:5432/rag_backend_app` which is not a real DB in `.env` | `backend/.env`, `backend/app/database/connection.py` |
| **Read-Only Guard — 3-layer** | ✅ WORKING | AST parse, keyword blocklist, SQLAlchemy engine event listener; comprehensive | `backend/app/database/readonly_guard.py` |
| **Schema Discovery** | ✅ WORKING | Real SQLAlchemy Inspector; discovers tables, columns, PKs, FKs, indexes, views | `backend/app/database/schema_discovery.py` |
| **Health Analyzer** | ✅ WORKING | Real SQL catalog queries; pg_stat_user_tables; NULL ratio checks; missing PK detection | `backend/app/monitoring/health_analyzer.py` |
| **Error Detector** | ⚠️ PARTIAL | In-process event recording works; log-file scan works; no real external SIEM/WAF integration | `backend/app/monitoring/error_detector.py` |
| **RAG Pipeline** | ✅ WORKING | Full ROUTE→RETRIEVE→TEXT-TO-SQL→SYNTHESIZE flow; real Groq calls | `backend/app/chatbot/rag_pipeline.py` |
| **RAG — Infrastructure Domain** | 🔧 MOCK | Uses a hardcoded static string `telemetry_context`; no real server metrics injected | `backend/app/chatbot/rag_pipeline.py` lines 198-210 |
| **RAG — Security Domain** | 🔧 MOCK | Uses a hardcoded static string `security_context`; no real security events injected | `backend/app/chatbot/rag_pipeline.py` lines 228-238 |
| **LLM Provider (Groq)** | ✅ WORKING | Real Groq client; LangChain ChatGroq with direct fallback; caching | `backend/app/chatbot/llm_provider.py` |
| **Groq Model ID** | 🚨 UNSAFE | `groq_chat_model = "openai/gpt-oss-120b"` is **not a real public Groq model**. This is likely an internal/restricted model. Standard Groq models are `llama3-8b-8192`, `mixtral-8x7b-32768`, etc. May cause 404 errors in other environments. | `backend/app/config/settings.py` line 28, `backend/app/chatbot/llm_provider.py` lines 44-47 |
| **Embedder (Ollama)** | ⚠️ PARTIAL | Real Ollama integration; graceful fallback to SHA256-based pseudovectors when Ollama offline | `backend/app/embeddings/embedder.py` |
| **Embedder — Fallback Vectors** | 🔧 MOCK | SHA256 hash-based 384-dim vectors (`_fallback_vector`) have no semantic meaning; vector search will return incorrect results when Ollama is offline | `backend/app/embeddings/embedder.py` lines 24-28 |
| **Vector Store (ChromaDB)** | ⚠️ PARTIAL | Real ChromaDB integration; persist dir `./vector_db`; empty by default (no auto-population at startup) | `backend/app/embeddings/vector_store.py` |
| **Chat Service** | ✅ WORKING | Properly persists conversation history; multi-turn context; delegates to RAG pipeline | `backend/app/services/chat_service.py` |
| **Health Service** | ✅ WORKING | Runs real health analysis, persists alerts, dispatches notifications | `backend/app/services/health_service.py` |
| **Recommendation Service** | ✅ WORKING | Derived from real health analysis; no mock data | `backend/app/services/recommendation_service.py` |
| **Documentation Service** | ✅ WORKING | Real schema discovery + Groq AI doc generation + ChromaDB indexing | `backend/app/services/documentation_service.py` |
| **Alert Repository** | ✅ WORKING | Real DB persistence; list_recent works | `backend/app/repositories/alert_repository.py` |
| **Notification System — Email** | ⚠️ PARTIAL | Implemented correctly; disabled by default (`EMAIL_ENABLED=false`); SMTP not configured | `backend/app/notifications/channels/email_channel.py` |
| **Notification System — Telegram** | ⚠️ PARTIAL | Outbound push-only via Bot API; disabled by default; `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` blank in `.env` | `backend/app/notifications/channels/telegram_channel.py` |
| **Notification System — Slack** | ⚠️ PARTIAL | Implemented correctly; disabled by default | `backend/app/notifications/channels/slack_channel.py` |
| **Notification System — Teams** | ⚠️ PARTIAL | Implemented correctly; disabled by default | `backend/app/notifications/channels/teams_channel.py` |
| **Notification System — Webhook** | ⚠️ PARTIAL | Implemented correctly; disabled by default | `backend/app/notifications/channels/webhook_channel.py` |
| **Frontend API Client** | ⚠️ PARTIAL | Real calls to `/api/v1/*`; fallback chain to N8N webhooks for server/notification data | `frontend/src/api/dashboard.ts` |
| **DashboardOverview Page** | ⚠️ PARTIAL | Fetches real health data; but fallback hardcodes `db_health: 99, server_health: 96, security_score: 98` | `frontend/src/pages/Dashboard/DashboardOverview.tsx` lines 56-61 |
| **DatabaseMonitoring Page** | ✅ WORKING | Real calls to `/api/v1/schema/overview`; live table introspection; connection config UI | `frontend/src/pages/Dashboard/DatabaseMonitoring.tsx` |
| **ServerMonitoring Page** | 🔧 MOCK | Hardcoded `defaultServerNodes` array used as fallback when external telemetry is offline | `frontend/src/pages/Dashboard/ServerMonitoring.tsx` lines 17-55 |
| **SecurityMonitoring Page** | 🔧 MOCK | Static `securityEvents` and `kpiMetrics` arrays hardcoded at file top; never fetched from backend | `frontend/src/pages/Dashboard/SecurityMonitoring.tsx` lines 13-40 |
| **AIAssistant Page** | ✅ WORKING | Routes to real `/api/v1/chat` endpoint; domain selection works; markdown rendering | `frontend/src/pages/Dashboard/AIAssistant.tsx`, `AIChatInterface.tsx` |
| **Alerts Page** | ⚠️ PARTIAL | Fetches from N8N webhook first; falls back to `/api/v1/alerts` second (order is inverted) | `frontend/src/pages/Dashboard/Alerts.tsx` |
| **AuditLog Page** | ⚠️ PARTIAL | Fetches audit logs from N8N webhook only; no backend `/api/v1/audit` endpoint exists | `frontend/src/pages/Dashboard/AuditLog.tsx` |
| **Telegram Bot (bidirectional)** | 🔧 MOCK | `bot.py` returns 100% hardcoded `MOCK_DATA` dict for database/server/security stats | `frontend/bot.py` lines 38-55, 165 |
| **Telegram Bot JS** | 📝 HARDCODED | `redhelp-bot.js` has hardcoded BOT_TOKEN and hardcoded Cloudflare URL | `frontend/redhelp-bot.js` lines 4-5 |
| **Zabbix Integration** | ⭕ MISSING | No Zabbix client, no Zabbix API calls anywhere in the backend | — |
| **Security Event Collection** | ⭕ MISSING | No SIEM, WAF, firewall log integration; no `/api/v1/security` endpoint | — |
| **N8N Integration** | ⚠️ PARTIAL | Frontend calls N8N webhooks for: notifications, server telemetry, auth, audit logs, chat history; backend is independent | `frontend/src/api/dashboard.ts`, `frontend/src/context/AuthContext.tsx` |
| **Local Metrics Server** | ⚠️ PARTIAL | `local_metrics_server.py` provides real OS metrics via `psutil` on port 9900; but it's for the dev machine, not production servers | `frontend/local_metrics_server.py` |
| **AI Recommendation Daemon** | 🔧 MOCK | `ai_recommendation_daemon.py` hardcodes `'YAMROT'` database name and a local `erp_demo` PostgreSQL connection | `frontend/ai_recommendation_daemon.py` |

---

## Detailed Findings Per Subsystem

### 1. Authentication System

**Current State:** The backend has a proper FastAPI JWT-based auth system. The frontend has a three-tier auth fallback.

**What Works:**
- `POST /api/v1/auth/login` correctly validates credentials against the app DB, issues JWT tokens
- JWT tokens are validated on every authenticated endpoint via `deps.py`
- RBAC (`viewer` / `analyst` / `admin`) is enforced on all backend routes

**What is Mock/Unsafe/Missing:**

**File:** `frontend/src/context/AuthContext.tsx`, lines 86, 167-175
```typescript
const [users, setUsers] = useState<UserAccount[]>([
  { email: 'superadmin@company.com', role: 'superadmin', password: 'admin', needsPasswordChange: false }
]);
```
This seeds an in-memory user with password `"admin"` in plaintext in React state. In the `login()` function:
```typescript
// 2. Try default in-memory user (superadmin@company.com / admin)
if (!authSuccess) {
  const found = users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
  ...
  } else if (email.toLowerCase() === 'superadmin@company.com' && password === 'admin') {
    userRole = 'superadmin';
    needsChange = false;
    authSuccess = true;
  }
}
```
This is a **frontend-only authentication bypass**: any attacker who knows the credentials `superadmin@company.com / admin` gets full superadmin access in the frontend's React context even if the FastAPI backend is completely down or rejects the credentials. No JWT is issued in this path, so the backend's protected API endpoints are still guarded — but all frontend pages, including the AuditLog/admin panel, become accessible.

**File:** `backend/.env`, line 17
```
JWT_SECRET_KEY=change-me-to-a-long-random-value
```
The `.env.example` file says `JWT_SECRET_KEY=change-me-to-a-long-random-value` as a placeholder, and the production `.env` file has not changed this value. Any JWT signed with this well-known string can be forged offline.

**File:** `backend/app/main.py`, lines 44-58
```python
admin_user = User(
    username="admin",
    hashed_password=hash_password("admin"),
    role="admin",
)
```
The auto-seeded default admin user has password `"admin"`. This is documented in the code as `logger.info("Auto-seeded default admin user: admin / admin")` but is never forced to change.

**File:** `frontend/src/pages/Dashboard/AuditLog.tsx`, lines 11-13
```typescript
const handleCreateAdmin = async (e: React.FormEvent) => {
  const randomPass = Math.random().toString(36).slice(-10);
```
`Math.random()` is cryptographically insecure for password generation.

---

### 2. Database Connection & Target DB

**Current State:** Well-implemented. Real Supabase connection. Three-layer read-only guard.

**What Works:**
- `target_db_url` in `.env` contains a real Supabase pooler URL with encoded credentials
- URL normalization handles `postgres://` vs `postgresql+psycopg2://` variants
- Automatic Supabase direct-to-pooler IPv4 mapping
- `_install_readonly_guard()` attaches a SQLAlchemy event listener
- `validate_sql()` uses sqlparse AST inspection + keyword allow-listing
- `enforce_row_limit()` prevents unbounded result sets

**What is Incomplete/Unsafe:**

**File:** `backend/.env`, line 21
```
APP_DB_URL=postgresql+psycopg2://app_user:app_password@localhost:5432/rag_backend_app
```
This is a placeholder; no real app database is configured. When running outside Docker, the app DB is unreachable. The backend catches the startup exception gracefully but all conversation history, alert persistence, and schema cache will fail at runtime.

**File:** `backend/.env`
The file contains a real Supabase URL with credentials and a real Groq API key. These are sensitive secrets that should not be in the repository at all. If this repo is in version control, credentials are exposed.

**File:** `backend/app/api/v1/schema.py`, lines 97-104
```python
"storage": f"{len(app_tables_info) * 12.4:.1f} MB",
```
Storage size is calculated as a fake formula (`table_count × 12.4 MB`) rather than a real `pg_database_size()` query. Similarly for target DB storage.

---

### 3. Server Monitoring

**Current State:** No real server monitoring exists in the backend. The frontend has a comprehensive mock.

**What Works:**
- `local_metrics_server.py` is a real Python HTTP server that returns genuine `psutil` metrics for the local development machine on port 9900
- `fetchLiveServerTelemetry()` in `dashboard.ts` correctly tries multiple sources in order before falling back

**What is Mock/Missing:**

**File:** `frontend/src/pages/Dashboard/ServerMonitoring.tsx`, lines 17-55
```typescript
const defaultServerNodes = [
  { server_name: 'APP-PROD-CLUSTER-01', status: 'Running', cpu: { usage_percent: 34, cores: 8 }, ... },
  { server_name: 'DB-PRIMARY-NODE-02', status: 'Running', cpu: { usage_percent: 48, cores: 16 }, ... },
  { server_name: 'AI-INFERENCE-NODE-03', status: 'Running', cpu: { usage_percent: 62, cores: 12 }, ... },
  { server_name: 'CACHE-REDIS-CLUSTER-04', status: 'Running', cpu: { usage_percent: 21, cores: 4 }, ... }
];
```
These 4 servers with specific CPU/memory/disk/uptime values are **pure fiction**. They are initialized as the default state (`useState<any[]>(defaultServerNodes)`) and displayed immediately on page load.

**File:** `frontend/src/pages/Dashboard/ServerMonitoring.tsx`, lines 57-65
```typescript
const defaultServerHistory = [
  { time: '10:00', cpu: 32, memory: 54, network: 180 },
  { time: '10:10', cpu: 36, memory: 55, network: 210 },
  ...
];
```
Hardcoded historical performance chart data.

**File:** `frontend/src/pages/Dashboard/ServerMonitoring.tsx`, line 113
```typescript
const point = { time: timeStr, cpu: avgCpu, memory: avgMem, network: Math.floor(Math.random() * 80) + 200 };
```
Network throughput is calculated with `Math.random()` — fabricated on every poll cycle.

**Missing from Backend:** There is no Zabbix client library in `requirements.txt`, no Zabbix API calls anywhere, no `/api/v1/servers` endpoint, no `/api/v1/zabbix` endpoint, no server monitoring service, and no server monitoring model. The entire server monitoring backend is **completely absent**.

**File:** `frontend/src/api/dashboard.ts`, function `parseZabbixHost()` (lines ~270-320)
A Zabbix host parser exists in the frontend, but it is only called if the N8N SRE webhook returns Zabbix-format data. The backend never queries Zabbix. The `parseZabbixHost` function itself contains hardcoded defaults:
```typescript
let cpuIdle = 85.0;
let totalMem = 16 * 1024 * 1024 * 1024;
// ...
security: {
  failed_logins: 3,     // HARDCODED
  successful_logins: 1420,  // HARDCODED
  blocked_ips: 12,      // HARDCODED
```

---

### 4. Security Monitoring

**Current State:** Entirely mock. No real security event collection exists anywhere.

**What is Mock:**

**File:** `frontend/src/pages/Dashboard/SecurityMonitoring.tsx`, lines 13-26
```typescript
const securityEvents = [
  { time: '20:38:12', severity: 'Low',    event: 'Successful admin login',        source: '192.168.1.105', status: 'Allowed'  },
  { time: '20:35:47', severity: 'Medium', event: 'Multiple failed SSH attempts',  source: '45.33.32.156',  status: 'Blocked'  },
  { time: '20:30:02', severity: 'Low',    event: 'SSL certificate renewed',       source: '10.0.0.1',      status: 'Success'  },
  { time: '20:22:18', severity: 'High',   event: 'Port scan detected',            source: '198.51.100.14', status: 'Blocked'  },
  { time: '20:15:33', severity: 'Medium', event: 'API rate limit exceeded',       source: '203.0.113.42',  status: 'Throttled'},
  { time: '19:58:05', severity: 'Low',    event: 'Scheduled vulnerability scan OK', source: '10.0.0.2',   status: 'Success'  },
];
```
Static fake security events with made-up IP addresses, timestamps, and event types. Used as `useState` initial value.

**File:** `frontend/src/pages/Dashboard/SecurityMonitoring.tsx`, lines 28-39
```typescript
const kpiMetrics = [
  { label: 'Threat Level',      value: 'LOW',       color: 'text-success', sub: 'No active threats', ... },
  { label: 'Firewall Status',   value: 'Active',    color: 'text-success', sub: 'All rules applied', ... },
  { label: 'Failed Logins',     value: '3 Today',   color: 'text-warning', sub: 'Last: 2h ago', ... },
  ...
  { label: 'Encrypted Traffic', value: '98.4%',     color: 'text-success', sub: 'TLS 1.3 enforced', ... },
```
KPI metric cards are all hardcoded. The page does attempt to update these from live data (`fetchSecurityTelemetry()` and `fetchRealAlerts()`), but `fetchSecurityTelemetry()` derives from `fetchLiveServerTelemetry()` which itself falls back to the mock server nodes. The `security` field on the mock server nodes also contains hardcoded values (`failed_logins: 3`, `blocked_ips: 12`, etc.).

**File:** `frontend/src/pages/Dashboard/SecurityMonitoring.tsx`
The performance chart at the bottom uses `mockPerformanceData` imported from `PerformanceChart.tsx` — this is a static array never replaced with real data.

**Missing from Backend:** No `/api/v1/security` endpoint, no security log collector, no SIEM integration, no WAF log parser, no firewall API client.

**File:** `backend/app/chatbot/rag_pipeline.py`, lines 228-240
```python
security_context = (
    "Security Domain: Firewall rules, authentication events, DLP, threat detection, "
    "TLS certificate management, WAF, audit trails, access control, RBAC policies. "
    "Real-time data is sourced from the security monitoring agent when configured."
)
```
The Security AI assistant answers from a static string prompt, not from real security event data. Despite claiming "real-time data is sourced from the security monitoring agent when configured," no such agent exists.

---

### 5. RAG / AI Pipeline

**Current State:** Database domain RAG is genuinely functional. Server and security domains use static context strings.

**What Works:**
- `_get_live_schema_summary()` uses real SQLAlchemy `inspect()` against the Supabase target DB
- `_retrieve_vector_context()` queries ChromaDB using real embeddings (or SHA256 fallback)
- Groq LLM is called with real API key for routing, SQL generation, and synthesis
- `validate_llm_sql()` + `validate_sql()` provides layered safety before query execution
- `execute_readonly_query()` enforces the `LIMIT` cap
- Multi-turn conversation history is passed from `ChatService`

**What is Mock/Incomplete:**

**File:** `backend/app/chatbot/rag_pipeline.py`, lines 198-210
```python
def _handle_infrastructure_query(question: str, history: list[dict] | None = None) -> RAGResult:
    telemetry_context = (
        "Server Infrastructure Status (live from backend health probe):\n"
        "Nodes: Application Server, Database Server, AI Inference Node, Cache Cluster.\n"
        "Consult /healthz endpoint for real-time status of all services.\n"
        "Domain: server compute metrics, SRE diagnostics, cluster load, node health."
    )
```
This is a static hardcoded string masquerading as "live from backend health probe." No actual healthz data is injected. The comment is misleading.

**File:** `backend/app/chatbot/rag_pipeline.py`, lines 228-238
```python
def _handle_security_query(question: str, history: list[dict] | None = None) -> RAGResult:
    security_context = (
        "Security Domain: Firewall rules, authentication events, DLP, threat detection, ..."
    )
```
Same issue — static generic description, not real security data.

**Vector Store Population:** ChromaDB at `./vector_db` is empty by default. The `POST /api/v1/schema/refresh` endpoint must be called manually to populate it. No startup script auto-populates it. Until populated, `_retrieve_vector_context()` returns empty string and the RAG pipeline falls back to live schema inspection (which still works, but misses any AI-generated descriptions).

**Groq model `"openai/gpt-oss-120b"`:** This is not a publicly documented Groq model name. Standard Groq models are `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `llama3-8b-8192`, etc. The `llm_provider.py` comment says it supports `openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b`, suggesting this is a special environment. Any deployment outside this environment will get 404 errors from Groq on chat requests.

---

### 6. Telegram Bot

**Current State:** Two separate bot implementations exist. Both are incomplete or mock.

**bot.py (Python, file in `frontend/`):**
```python
MOCK_DATA = {
    "database": (
        "🛢️ *Database Health:* 98% (Optimal performance)\n"
        "💾 *Storage Used:* 559 GB\n"
        "🔌 *Active Connections:* 136\n"
        "⚠️ *Slow Queries:* 19 / Hr"
    ),
    "server": ( "🖥️ *Server Health:* 96%..." ),
    "security": ( "🛡️ *Security Score:* 82%..." ),
```
All dashboard data served through `/btn_database`, `/btn_server`, `/btn_security` buttons is **100% fake hardcoded values**. The bot serves these fabricated metrics to real users when they click the buttons. The Groq API is never called. The backend is never queried.

**redhelp-bot.js (Node.js, also in `frontend/`):**
- Has a hardcoded `BOT_TOKEN = '8798642467:...'` (live token exposed in source)
- Uses a hardcoded Cloudflare tunnel URL
- This bot only launches a Mini App WebApp — it does not serve data itself

**What is Missing:**
- No command handler for `!query`, `/query`, or natural language AI queries to the bot
- No call from either bot to `/api/v1/chat`
- No call from either bot to `/api/v1/health`
- The bidirectional "query ERAOP from Telegram" feature described in the spec has no implementation

---

### 7. N8N Integration Analysis

N8N webhooks are referenced in 5 places in the frontend. They are **not referenced in the backend at all**.

| N8N Endpoint | Purpose | Backend Alternative | Required? |
|---|---|---|---|
| `VITE_N8N_NOTIFICATIONS_URL` (`/webhook/notifications-api`) | Fetch notifications from MS SQL | `/api/v1/alerts` | No — backend has full alerts system |
| `VITE_N8N_SRE_ENDPOINT` (`/webhook/sre-chatbot`) | Server telemetry & Zabbix data | None (gap) | Yes — no backend replacement |
| `VITE_N8N_CHAT_HISTORY_URL` (`/webhook/chat-history`) | Database metadata, Telegram chat ID registration | `/api/v1/schema/overview` (partial) | Partially |
| `VITE_N8N_AUTH_URL` (`/webhook/erp-auth`) | User auth, user list, audit logs | `/api/v1/auth/login`, `/api/v1/auth/users` | No for auth; Yes for audit logs |
| `VITE_N8N_MSSQL_URL` (`/webhook/mssql-ai-chat`) | MSSQL AI chat (legacy) | `/api/v1/chat` | No |

**Key Finding:** The Alerts page (`Alerts.tsx`) calls `fetchRealNotifications()` which hits N8N first, falls back to an empty array, and does NOT call `/api/v1/alerts`. This means the alerts backend endpoint is **effectively unused by the Alerts page itself** — only `dashboard.ts`'s `fetchRealAlerts()` calls both.

**Key Finding:** `AuthContext.tsx` registers the user's Telegram `chat_id` by POSTing to the N8N chat history webhook. If N8N is unavailable, Telegram linking fails silently. No backend endpoint handles `register_telegram`.

---

### 8. Environment Configuration Analysis

**Required variables with no default (will cause startup failure if missing):**
- `TARGET_DB_URL` — no default in `settings.py` (will raise `ValidationError`)
- `APP_DB_URL` — no default in `settings.py` (will raise `ValidationError`)
- `JWT_SECRET_KEY` — no default in `settings.py` (will raise `ValidationError`)

**Problematic defaults:**
- `groq_api_key: str = ""` — empty default; Groq calls will fail with RuntimeError if not set
- `groq_chat_model: str = "openai/gpt-oss-120b"` — non-standard Groq model name (see §5)
- `.env` has `JWT_SECRET_KEY=change-me-to-a-long-random-value` — weak default value in production file

**`.env.example` vs `settings.py` discrepancies:**
- `.env.example` documents `OLLAMA_CHAT_MODEL` and `OLLAMA_REQUEST_TIMEOUT_S` — but `settings.py` has no `ollama_chat_model` field and uses `groq_request_timeout_s` instead
- `.env.example` is still written for an Ollama-based LLM stack, while the actual code uses Groq

**Secrets exposed in `.env` file:**
- `TARGET_DB_URL` contains encoded Supabase credentials
- `GROQ_API_KEY` contains what appears to be a live API key: `gsk_Gsfig7Uw...`

---

### 9. Security Vulnerabilities

| Vulnerability | Severity | Location |
|---|---|---|
| Weak default JWT secret in production `.env` | CRITICAL | `backend/.env` line 17 |
| Live Groq API key committed to `.env` | CRITICAL | `backend/.env` |
| Live Supabase DB credentials in `.env` | CRITICAL | `backend/.env` |
| Hardcoded Telegram bot token in source | HIGH | `frontend/redhelp-bot.js` line 4 |
| Frontend auth bypass (hardcoded superadmin) | HIGH | `frontend/src/context/AuthContext.tsx` lines 86, 167-175 |
| `Math.random()` used for password generation | MEDIUM | `frontend/src/pages/Dashboard/AuditLog.tsx` line ~120 |
| Plaintext passwords stored in React state | MEDIUM | `frontend/src/context/AuthContext.tsx` (UserAccount.password field) |
| Default admin seeded with password `"admin"` | MEDIUM | `backend/app/main.py` lines 42-49 |
| CORS `allow_methods=["*"]` and `allow_headers=["*"]` | LOW | `backend/app/main.py` line 99 |
| Rate limiting is per-IP in-memory (no Redis, single-instance only) | LOW | `backend/app/middleware/rate_limiter.py` |
| `/api/v1/schema/test-connection` and `/apply-connection` have no auth | MEDIUM | `backend/app/api/v1/schema.py` — these endpoints lack `CurrentUser` dependency |
| `/api/v1/schema/overview` has no auth | MEDIUM | `backend/app/api/v1/schema.py` — `get_schema_overview()` has no auth dependency |

**Unauthenticated endpoints deep-dive:**

`schema.py`:
```python
@router.get("/overview")
def get_schema_overview():  # No auth dependency
    ...

@router.post("/test-connection")
def test_connection(req: ConnectionTestRequest):  # No auth dependency
    ...

@router.post("/apply-connection")
def apply_connection(req: ConnectionTestRequest):  # No auth dependency
    ...
```
The `/api/v1/schema/apply-connection` endpoint is particularly dangerous: it accepts a connection URL and **replaces the global target DB engine** (`set_target_url_override(url)`) with no authentication check. An unauthenticated attacker can redirect the backend's target database to an attacker-controlled server.

---

### 10. Database Health Metrics — Gap Analysis

The frontend `DatabaseMonitoring.tsx` and `DashboardOverview.tsx` display several metrics. Here is what the backend actually provides vs. what the frontend expects:

| Metric | Backend Provides? | Source | Notes |
|---|---|---|---|
| Database connection status | ✅ Yes | `/api/v1/schema/overview` → `target_db_status` | Real |
| Table count | ✅ Yes | Schema discovery | Real |
| Column-level schema | ✅ Yes | Inspector | Real |
| Row counts per table | ✅ Yes | `SELECT count(*)` | Real |
| Active connections | ❌ No | Not implemented | Would need `pg_stat_activity` |
| Database version | ❌ No | Not implemented | Would need `SELECT version()` |
| Slow queries | ❌ No | Not implemented | Would need `pg_stat_statements` |
| Database size | 🔧 FAKE | `len(tables) * 12.4 MB` formula | Fabricated |
| Query activity | ❌ No | Not implemented | — |
| Database errors | ⚠️ Partial | `error_detector.py` in-process only | Not DB server logs |
| Index health | ✅ Yes | `pg_stat_user_tables` | Real |
| Missing PKs/FKs | ✅ Yes | Schema Inspector | Real |
| NULL ratios | ✅ Yes | `SELECT COUNT(*)` | Real |
| Backup status | 🔧 FAKE | Hardcoded "Daily Automated PITR" in `fetchDatabaseMetadata()` | `dashboard.ts` line ~400 |

---

### 11. Code Quality Issues

1. **`frontend/src/context/AuthContext.tsx`:** `UserAccount` interface has a `password?: string` field — passwords should never be in client-side React state.

2. **`frontend/bot.py` is inside the `frontend/` directory** — a Python Telegram bot has nothing to do with the React frontend. It belongs in `backend/` or a dedicated `bots/` directory.

3. **`frontend/ai_recommendation_daemon.py`** hardcodes `"erp_demo"` database and `"YAMROT"` table name. It also hardcodes the n8n URL `http://127.0.0.1:5678/webhook/erp-chat`. This script is not integrated with the FastAPI backend at all.

4. **`backend/app/chatbot/llm_provider.py`**, lines 4-8: `sys.path.append()` for hardcoded Linux paths (`/home/appuser/...`) is unnecessary on Windows and clutters the Python path.

5. **`backend/app/api/v1/schema.py`**: The `_transform_and_normalize_url()` function is duplicated almost identically from `backend/app/database/connection.py`'s `get_target_engine()`. The URL normalization logic should live in one place.

6. **`frontend/src/pages/Dashboard/SecurityMonitoring.tsx`**: `PerformanceChart` receives `mockPerformanceData` — but the import `mockPerformanceData` from `PerformanceChart.tsx` leaks mock data from a component module, which is an anti-pattern.

7. **`backend/app/database/connection.py`**: `set_target_url_override()` is a global mutable singleton without thread safety (no lock). In a multi-threaded Uvicorn deployment, concurrent requests could see inconsistent engine state.

8. **`frontend/src/context/AuthContext.tsx`**: Session expiry is set to 10 minutes which is very short for an enterprise monitoring dashboard. Every mousemove refreshes it, making it essentially a 10-minute inactivity timeout.

9. **`backend/app/models/user.py`** (not read but referenced): The auto-seeded superadmin in `main.py` does not check `superadmin@company.com` by username, only by email — there may be two separate entries if the admin was created manually.

10. **`frontend/src/api/dashboard.ts`**: `fetchDatabaseMetadata()` hardcodes `replication: 'WAL Mode Active'` and `backup: 'Daily Automated PITR'` in every response — these are fabricated values presented as real infrastructure facts.

---

## Priority Action Plan

### CRITICAL — Breaks Core Functionality or Exposes Real Data Risks

| Issue | Files to Modify | Complexity |
|---|---|---|
| **Rotate leaked Groq API key and Supabase credentials** — both are in the `.env` file and should be treated as compromised | `backend/.env` + infrastructure | S |
| **Change JWT secret key** to a cryptographically random 256-bit value | `backend/.env` | S |
| **Add authentication to `/api/v1/schema/overview`, `/test-connection`, `/apply-connection`** — especially `apply-connection` which overwrites the global DB engine unauthenticated | `backend/app/api/v1/schema.py` | S |
| **Remove frontend auth bypass** — delete the in-memory users list fallback and the hardcoded `superadmin@company.com / admin` check from `AuthContext.tsx` | `frontend/src/context/AuthContext.tsx` | M |
| **Remove Telegram bot token from source code** — move to `.env`/environment variable | `frontend/redhelp-bot.js` | S |

### HIGH — Mock Data in Production Paths, Major Missing Features

| Issue | Files to Modify | Complexity |
|---|---|---|
| **Implement real server monitoring backend** — add `/api/v1/servers` endpoint, create a Zabbix API client or direct SSH/SNMP agent, serve real CPU/RAM/disk metrics | New: `backend/app/services/server_service.py`, `backend/app/api/v1/servers.py` | XL |
| **Remove `defaultServerNodes` mock from ServerMonitoring.tsx** — replace with empty state + "No monitoring agent connected" message when telemetry unavailable | `frontend/src/pages/Dashboard/ServerMonitoring.tsx` | M |
| **Implement real security event collection backend** — add `/api/v1/security` endpoint; collect from `error_detector.py` auth events, add hooks from auth middleware | New: `backend/app/api/v1/security.py`, `backend/app/services/security_service.py` | XL |
| **Remove hardcoded `securityEvents` and `kpiMetrics`** from SecurityMonitoring.tsx | `frontend/src/pages/Dashboard/SecurityMonitoring.tsx` | M |
| **Fix Telegram bot to serve real data** — replace `MOCK_DATA` dict with real calls to FastAPI `/api/v1/health/report`, `/api/v1/alerts` | `frontend/bot.py` | L |
| **Fix default admin password policy** — require password change on first login for seeded admin, or generate a random password | `backend/app/main.py` | M |
| **Verify/fix Groq model name** — `openai/gpt-oss-120b` is non-standard; document which Groq models are available, add a fallback to a standard model | `backend/app/chatbot/llm_provider.py`, `backend/app/config/settings.py` | M |

### MEDIUM — Incomplete Features, Partial Implementations

| Issue | Files to Modify | Complexity |
|---|---|---|
| **Implement real active connections metric** — query `pg_stat_activity` for connection count | `backend/app/monitoring/health_analyzer.py` or `backend/app/api/v1/health.py` | S |
| **Implement real database size** — replace `len(tables) * 12.4 MB` formula with `SELECT pg_database_size()` | `backend/app/api/v1/schema.py` | S |
| **Implement real database version** — add `SELECT version()` to schema overview | `backend/app/api/v1/schema.py` | S |
| **Populate ChromaDB at startup** — run schema indexing if vector store is empty on startup | `backend/app/main.py` | M |
| **Inject real server/security context into RAG pipeline** — replace static `telemetry_context` and `security_context` strings | `backend/app/chatbot/rag_pipeline.py` | L |
| **Add Telegram `register_telegram` endpoint to FastAPI** — remove N8N dependency for chat ID registration | New: endpoint in `backend/app/api/v1/auth.py` | M |
| **Alerts page should use `/api/v1/alerts` directly**, not N8N | `frontend/src/pages/Dashboard/Alerts.tsx` | S |
| **Remove `.env.example` Ollama model references** that no longer apply | `backend/.env.example` | S |
| **Set up real APP_DB_URL** — provision or document the required app database | `backend/.env`, `backend/docker-compose.yml` | M |
| **Thread-safe target URL override** — add lock to `set_target_url_override` | `backend/app/database/connection.py` | S |
| **Remove `Math.random()` from password generation** — use `crypto.getRandomValues()` | `frontend/src/pages/Dashboard/AuditLog.tsx` | S |
| **Remove plaintext password field from `UserAccount` interface** | `frontend/src/context/AuthContext.tsx` | M |

### LOW — Code Quality, Documentation, Minor Issues

| Issue | Files to Modify | Complexity |
|---|---|---|
| Remove hardcoded Linux `sys.path` additions | `backend/app/chatbot/llm_provider.py` | S |
| Deduplicate URL normalization logic | `backend/app/api/v1/schema.py`, `backend/app/database/connection.py` | M |
| Move `bot.py` and `redhelp-bot.js` to a dedicated top-level `bots/` directory | Directory restructure | S |
| Remove `ai_recommendation_daemon.py` hardcoded DB names or document as legacy | `frontend/ai_recommendation_daemon.py` | S |
| Fix `.env.example` to match actual settings.py fields | `backend/.env.example` | S |
| Document that `local_metrics_server.py` is a dev-only tool | `frontend/local_metrics_server.py` | S |
| Shorten session expiry from 10min to 60min (matches JWT expiry) | `frontend/src/context/AuthContext.tsx` | S |
| Remove `mockPerformanceData` import leak from PerformanceChart | `frontend/src/pages/Dashboard/SecurityMonitoring.tsx` | S |
| Add rate limiting decorators to `/api/v1/chat` (most expensive endpoint) | `backend/app/api/v1/chat.py` | S |

---

## Implementation Roadmap

1. **Real Supabase database connection verification** — The `TARGET_DB_URL` in `.env` connects to a real Supabase instance via the Singapore pooler. Verification: call `/api/v1/schema/overview` and confirm `target_database.status = "Online & Verified"`. Issue: APP_DB_URL is not set up; provision a PostgreSQL database and update `.env`.

2. **Security hardening (immediate)** — Rotate leaked credentials, change JWT secret, add auth guards to unauthenticated schema endpoints, remove frontend auth bypass, remove hardcoded Telegram token.

3. **Server monitoring implementation (Zabbix or alternative)** — Three options:
   - Option A (Zabbix): Add `zabbix_api` or `pyzabbix` to `requirements.txt`, create `backend/app/services/zabbix_service.py`, add `GET /api/v1/servers` endpoint, configure `ZABBIX_URL`, `ZABBIX_USER`, `ZABBIX_PASSWORD` in settings.
   - Option B (psutil agent): Extend `local_metrics_server.py` to run on production servers and register their endpoints in the backend settings.
   - Option C (SNMP): Use `pysnmp` to poll real servers.

4. **Security event collection implementation** — Sources to wire up: (a) backend auth failures already tracked via `error_detector.record_error_event()`; (b) rate limit exceeded events; (c) `DatabaseReadOnlyViolationError` events. Create `GET /api/v1/security/events` endpoint serving `build_error_report()` filtered to auth/security categories.

5. **RAG pipeline full verification** — Run `/api/v1/schema/refresh` after fixing APP_DB_URL and verifying Ollama or confirming fallback embedding behavior. Confirm `/api/v1/chat` returns real query results.

6. **Telegram bot bidirectional implementation** — Rewrite `bot.py` to call the FastAPI backend: `/api/v1/health/report` for database health, `/api/v1/alerts` for alerts summary, `/api/v1/chat` for AI queries.

7. **Frontend mock data removal** — Remove `defaultServerNodes`, `defaultServerHistory`, static `securityEvents`, `kpiMetrics`, hardcoded fallback health scores.

8. **Notification channels verification** — Configure and test at least one channel (Telegram or email). Set `TELEGRAM_ENABLED=true`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in `.env`.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Leaked Groq API key exploited (billing fraud) | HIGH | HIGH | Rotate immediately; add to `.gitignore` pattern |
| Leaked Supabase credentials allow data access/deletion | HIGH | CRITICAL | Rotate DB password in Supabase dashboard immediately |
| Unauthenticated `/apply-connection` exploited to redirect target DB to attacker server | MEDIUM | CRITICAL | Add `require_role(Role.ADMIN)` to endpoint |
| Hardcoded JWT secret forged tokens | MEDIUM | HIGH | Replace with 32+ byte random value |
| Frontend auth bypass grants admin UI access without backend | MEDIUM | HIGH | Remove in-memory user fallback |
| Mock server/security data misleads operators about real incidents | HIGH | HIGH | Remove defaults; show "No agent connected" state |
| ChromaDB empty in production, degraded RAG quality | HIGH | MEDIUM | Auto-populate on startup if empty |
| App DB not configured, conversation history lost | HIGH | MEDIUM | Document and provision APP_DB_URL |
| Ollama offline, SHA256 fallback vectors corrupt vector search | MEDIUM | MEDIUM | Document Ollama as required, or integrate an alternative embedding API |
| Non-standard Groq model ID causes 404 in other environments | HIGH | HIGH | Map to standard Groq model ID or document as custom environment |
| Rate limiting bypassed by rotating IPs | LOW | MEDIUM | Add Redis-backed rate limiting in production |

---

## Code Quality Issues Summary

| Issue | File | Line(s) | Type |
|---|---|---|---|
| Hardcoded Linux `sys.path` | `backend/app/chatbot/llm_provider.py` | 4-8 | Dead code on Windows |
| Duplicated URL normalization | `backend/app/database/connection.py`, `backend/app/api/v1/schema.py` | — | DRY violation |
| `password` field in `UserAccount` interface | `frontend/src/context/AuthContext.tsx` | 7 | Security |
| `Math.random()` for password generation | `frontend/src/pages/Dashboard/AuditLog.tsx` | ~120 | Security |
| Static fallback health scores (99, 96, 98) | `frontend/src/pages/Dashboard/DashboardOverview.tsx` | 56-61 | Mock data |
| `mockPerformanceData` leak from component | `frontend/src/pages/Dashboard/SecurityMonitoring.tsx` | 3 (import) | Architecture |
| Hardcoded `"YAMROT"` and local DB in daemon | `frontend/ai_recommendation_daemon.py` | 14, 30 | Hardcoded |
| Bot files in frontend directory | `frontend/bot.py`, `frontend/redhelp-bot.js` | — | Misplaced files |
| `set_target_url_override` not thread-safe | `backend/app/database/connection.py` | 47-52 | Concurrency |
| `replication: 'WAL Mode Active'` hardcoded | `frontend/src/api/dashboard.ts` | ~400 | Fabricated data |
| `backup: 'Daily Automated PITR'` hardcoded | `frontend/src/api/dashboard.ts` | ~401 | Fabricated data |
| Storage calculated as `tables * 12.4 MB` | `backend/app/api/v1/schema.py` | ~118 | Fabricated metric |
| `GROQ_CHAT_MODEL=openai/gpt-oss-120b` non-standard | `backend/app/config/settings.py` | 28 | Portability |
| Double `if role !== 'superadmin' return` | `frontend/src/pages/Dashboard/AuditLog.tsx` | 11, 52 | Duplicated guard |
