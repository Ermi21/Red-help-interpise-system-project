"""
Multi-system text chunking and knowledge corpus generation for the Enterprise RAG System.

Splits documentation, system specifications, operational runbooks, and schema text into
semantically coherent embedding-sized chunks enriched with metadata across all 3 enterprise systems:
  1. Database System (PostgreSQL schema, PgBouncer pooler, cache hit ratios, query AST safety)
  2. Server & Infrastructure System (Compute nodes, CPU/RAM/Disk metrics, Docker cluster topology, SRE runbooks)
  3. Security System (Zero-Trust WAF, 247 firewall rules, brute-force defense, audit trail compliance)
"""
from typing import List, Tuple
try:
    from langchain_core.documents import Document
except ImportError:
    class Document:  # type: ignore
        def __init__(self, page_content: str, metadata: dict = None):
            self.page_content = page_content
            self.metadata = metadata or {}
        def __repr__(self):
            return f"Document(page_content={self.page_content[:40]}..., metadata={self.metadata})"

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    _splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
except ImportError:
    class _SimpleSplitter:  # type: ignore
        def split_text(self, text: str) -> list[str]:
            return [p.strip() for p in text.split("\n\n") if p.strip()] or [text]
    _splitter = _SimpleSplitter()


def chunk_text(text: str, metadata: dict) -> list[Document]:
    """Split `text` into overlapping chunks, each tagged with `metadata` so
    retrieved chunks can always be traced back to their source table/doc."""
    if not text or not text.strip():
        return []
    chunks = _splitter.split_text(text)
    return [Document(page_content=chunk, metadata=metadata) for chunk in chunks]


def chunk_documents(items: list[tuple[str, dict]]) -> list[Document]:
    """Bulk variant of chunk_text over a list of (text, metadata) pairs."""
    documents: list[Document] = []
    for text, metadata in items:
        documents.extend(chunk_text(text, metadata))
    return documents


def get_3systems_knowledge_corpus() -> list[tuple[str, dict]]:
    """
    Returns curated enterprise documentation across all three infrastructure systems:
    Database, Server / Infrastructure, and Security.
    """
    corpus: list[tuple[str, dict]] = [
        # ═════════════════════════════════════════════════════════════════════════
        # SYSTEM 1: DATABASE SYSTEM
        # ═════════════════════════════════════════════════════════════════════════
        (
            """### PostgreSQL Architecture & Connection Pooler Specifications
The Enterprise Database operates on PostgreSQL 16.3 with high-availability transaction pooling.
Target Cloud Engine: Remote Supabase PostgreSQL instance located at aws-0-ap-southeast-1.pooler.supabase.com on Port 6543 (transaction mode pooler with SSL enforced).
Operational Application DB: Local PostgreSQL 16 instance named 'rag_backend_app' on Port 5432 storing system metadata, user accounts, audit trails, and alerts.
Buffer Cache Hit Ratio: Maintained at >99.0% by allocating dedicated shared_buffers (256MB on operational node). When cache hit ratio drops below 95%, investigate sequential scans and cold disk reads.
Connection Limits: Max 100 concurrent pooled connections. PgBouncer transaction-mode pooling recycles connections immediately after transaction commit, preventing client connection starvation. Statement timeout is strictly capped at 15,000 milliseconds (15s) for all analytical queries.""",
            {
                "system": "database",
                "category": "architecture",
                "title": "PostgreSQL Architecture & Connection Pooler Specifications",
                "keywords": "postgresql, pgbouncer, pooler, connection limits, buffer cache hit, shared_buffers, supabase",
                "source": "database_specs"
            }
        ),
        (
            """### Database Schema & Table Catalog
The enterprise database catalog contains the following core operational tables:
1. `users`: Enterprise user accounts, usernames, email addresses, hashed bcrypt passwords, roles ('admin', 'superadmin'), active status, and audit timestamps.
2. `alerts`: System incident alerts across all 3 systems (database, server, security). Fields include severity ('low', 'medium', 'high', 'critical'), status ('active', 'resolved'), category, title, description, and AI-recommended action.
3. `audit_logs`: Immutable compliance trail logging user identity, IP address, user agent, endpoint invoked, action performed, and timestamp.
4. `login_events`: Authentication security logs tracking successful and failed login attempts, client IP, device classification ('desktop', 'mobile'), and failure reason.
5. `system_metrics`: High-resolution time-series metrics recording CPU usage, RAM allocation, disk capacity, and connection counts.
6. `conversations` & `messages`: Multi-turn conversational memory for the AI RAG Assistant, generated SQL queries, and source citations.""",
            {
                "system": "database",
                "category": "schema",
                "title": "Enterprise Database Schema & Tables Catalog",
                "keywords": "schema, tables, users, alerts, audit_logs, login_events, system_metrics, conversations, columns",
                "source": "database_catalog"
            }
        ),
        (
            """### Database Read-Only Security Guardrails & AST Safety
All database operations initiated by the AI Assistant or analytics engine are bound by strict Read-Only Privilege:
1. AST Parser Validation: Every candidate SQL statement passes through a 3-layer Abstract Syntax Tree (AST) validation parser using sqlparse. Only statements beginning with SELECT, WITH, EXPLAIN, SHOW, or DESCRIBE are permitted.
2. Prohibited Statements: Any statement containing INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, or COPY is immediately intercepted and blocked before reaching the database engine.
3. Transaction Isolation: Queries run in READ ONLY transaction isolation mode (SET TRANSACTION READ ONLY) with statement_timeout=15000ms.
4. Schema Modification Protection: The AI assistant has zero schema modification privileges. Database integrity is preserved at both the application middleware and database role levels.""",
            {
                "system": "database",
                "category": "policy",
                "title": "Database Read-Only Security Guardrails & AST Safety",
                "keywords": "read-only, sql safety, ast parser, forbidden statements, drop, truncate, delete, select only",
                "source": "database_security"
            }
        ),
        (
            """### Database Query Optimization & Indexing Runbook
When slow query alerts or high query latency (>50ms) are detected:
1. Identify Slow Queries: Query pg_stat_statements or pg_stat_activity to find queries with highest total_exec_time and mean_exec_time.
2. Inspect Query Execution Plans: Run EXPLAIN (ANALYZE, BUFFERS) on the target query. Look for 'Seq Scan' (Sequential Scans) on tables with more than 1,000 rows.
3. Indexing Guidelines:
   - For equality filters (`WHERE user_id = ?`), create a standard B-tree index: `CREATE INDEX CONCURRENTLY idx_table_col ON table(col);`
   - For range queries and timestamps (`WHERE created_at > ?`), index the timestamp column.
   - For foreign key lookups, ensure all foreign key columns have indexes to prevent table-level share locks during joins.
4. Autovacuum & Bloat Maintenance: Ensure autovacuum is active to update table statistics and prevent dead tuple accumulation. Buffer cache hit ratio should remain above 99%.""",
            {
                "system": "database",
                "category": "runbook",
                "title": "Database Query Optimization & Indexing Runbook",
                "keywords": "query optimization, explain analyze, slow queries, b-tree index, autovacuum, dead tuples, seq scan",
                "source": "database_runbook"
            }
        ),

        # ═════════════════════════════════════════════════════════════════════════
        # SYSTEM 2: SERVER & INFRASTRUCTURE SYSTEM
        # ═════════════════════════════════════════════════════════════════════════
        (
            """### Server Infrastructure Compute & OS Specifications
The host server infrastructure runs on dedicated enterprise Linux x86_64 architecture:
Compute Nodes: 8 CPU cores @ 2.3 GHz base frequency with cgroups resource partitioning. Normal operating CPU utilization is <40.0%. CPU alerts trigger at >80.0% (Warning) and >90.0% (Critical).
Memory Allocation: 8 GB physical virtual memory (RAM). Memory distribution is monitored across resident set size (RSS), page cache, and buffer memory. Normal RAM utilization is <60.0%. Critical threshold is >85.0%.
Disk & Storage: NVMe solid-state storage mounted on root filesystem ('/'). Storage headroom alert triggers when disk usage exceeds 85.0%. Vector database persistence directory is located at '/app/vector_db'.
Load Averages: 1-minute, 5-minute, and 15-minute load averages reflect run queue depth. Stable load average for 8 cores is <4.00. High load (>7.00) indicates process contention or I/O wait bottleneck.""",
            {
                "system": "server",
                "category": "architecture",
                "title": "Server Infrastructure Compute & OS Specifications",
                "keywords": "server compute, cpu cores, memory, ram, disk storage, load average, uptime, linux x86_64",
                "source": "server_specs"
            }
        ),
        (
            """### Microservice Cluster Topology & Service Health
The infrastructure runs a unified containerized microservice cluster:
1. `fastapi-backend`: Port 8000. Core API Gateway, JWT authentication, RAG intelligence orchestrator, and WebSocket metric emitter. Health probe: `/healthz`.
2. `app-db`: Port 5432. PostgreSQL 16 operational database engine hosting application state, user schemas, and audit logs.
3. `redis`: Port 6379. In-memory cache and session broker utilizing volatile-lru eviction policy with 256MB memory cap.
4. `frontend-gateway`: Port 3000 / 5173. React 18 single-page application with Vite bundler and dark-mode telemetry dashboard.
5. `ollama-node`: Port 11434. Local inference and vector embedding service powering nomic-embed-text embeddings.
6. `supabase-pooler`: Port 6543 (Remote). Remote transaction pooler connecting to cloud PostgreSQL storage.
All internal services communicate across an isolated private Docker bridge network with no external port exposure except ports 80/443.""",
            {
                "system": "server",
                "category": "architecture",
                "title": "Microservice Cluster Topology & Service Health",
                "keywords": "microservices, docker containers, fastapi, redis, postgresql, ollama, frontend, ports, cluster nodes",
                "source": "server_topology"
            }
        ),
        (
            """### SRE High CPU & Memory Incident Response Runbook
Procedures for diagnosing and resolving server resource starvation:
1. High CPU Utilization (>80%):
   - Collect top consuming processes using `psutil.process_iter()`.
   - Identify if the bottleneck is CPU-bound (e.g. LLM embedding computation or complex sorting) or I/O wait (e.g. unindexed table scan).
   - If CPU is consumed by uvicorn worker threads, verify whether concurrent client traffic exceeds 60 req/min rate limit.
2. High Memory / OOM Threat (>85%):
   - Inspect resident memory: verify Redis cache usage and ChromaDB vector store memory footprint.
   - Flush inactive cache memory or restart idle worker tasks before Linux OOM killer is triggered.
3. System Uptime & Degraded Services:
   - Check service liveness via `/healthz`. If any container is degraded, check container logs in `./logs/` for traceback exceptions.""",
            {
                "system": "server",
                "category": "runbook",
                "title": "SRE High CPU & Memory Incident Response Runbook",
                "keywords": "sre runbook, high cpu, memory leak, oom killer, process monitoring, psutil, container restart",
                "source": "server_runbook"
            }
        ),

        # ═════════════════════════════════════════════════════════════════════════
        # SYSTEM 3: SECURITY & PERIMETER DEFENSE SYSTEM
        # ═════════════════════════════════════════════════════════════════════════
        (
            """### Zero-Trust Web Application Firewall (WAF) & Perimeter Defense
The Perimeter Defense system operates on a Zero-Trust architecture:
1. Web Application Firewall (WAF): Layer 7 deep packet inspection filters every incoming HTTP request. Payloads are scanned for Cross-Site Scripting (XSS), SQL Injection (SQLi), Path Traversal, and suspicious user-agent fingerprints.
2. 247 Dynamic Firewall Rules: The network firewall enforces 247 active rules isolating backend microservices, whitelisting trusted API endpoints, and blocking high-risk IP ranges. Default-deny policy on all non-whitelisted ingress ports.
3. Rate Limiting & Anti-DDoS: Enforced using SlowAPI token-bucket algorithm at 60 requests per minute per IP address. Rapid bursts exceeding threshold receive HTTP 429 Too Many Requests, neutralizing Layer 7 application DDoS attempts.
4. Transport Layer Security: TLS 1.3 enforced for all external HTTPS traffic with secure forward secrecy ciphers.""",
            {
                "system": "security",
                "category": "policy",
                "title": "Zero-Trust Web Application Firewall (WAF) & Perimeter Defense",
                "keywords": "security, waf, zero-trust, firewall rules, 247 rules, ddos mitigation, rate limiting, tls 1.3",
                "source": "security_waf"
            }
        ),
        (
            """### Identity Governance, Authentication & Brute-Force Lockout Policy
User authentication and access control policies:
1. Token Authentication: Secure JWT tokens signed with HS256 algorithm and 7-day expiration (10,080 minutes). Token payloads contain user ID, role, and username claims.
2. Role-Based Access Control (RBAC):
   - `superadmin`: Full enterprise access to all 3 monitoring systems (Database, Server, Security), user creation, role assignment, and system configurations.
   - `admin`: Operational access to monitoring dashboards, telemetry charts, AI RAG assistant, and alert tracking.
3. Brute-Force Protection: Tracks failed login attempts in localStorage and `login_events` table.
   - Max Failed Attempts: 5 attempts within a 5-minute sliding window.
   - Lockout Penalty: Exceeding 5 attempts triggers an automatic 15-minute account lockout (LOCKOUT_DURATION = 900 seconds).
   - Cold-Start Resilience: Connection timeouts and server spin-up delays do NOT count as failed password attempts.""",
            {
                "system": "security",
                "category": "policy",
                "title": "Identity Governance, Authentication & Brute-Force Lockout Policy",
                "keywords": "identity governance, authentication, jwt tokens, rbac, superadmin, admin, brute-force lockout, 5 attempts",
                "source": "security_identity"
            }
        ),
        (
            """### Cybersecurity Incident Response & Audit Trail Runbook
Procedures for investigating security alerts and unauthorized access attempts:
1. Brute-Force Attack Response:
   - Query `login_events` for recent failures (`SELECT client_ip, count(*) FROM login_events WHERE success = false GROUP BY client_ip HAVING count(*) >= 5`).
   - Extract attacker IP and append to dynamic firewall blocklist.
   - Force session termination and invalidate tokens for the targeted account.
2. SQL Injection Attempt Containment:
   - When AST parser intercepts unauthorized SQL syntax, an immediate High-severity alert is created in `alerts` table.
   - Review client IP, query string, and user-agent in `audit_logs` table.
3. Cross-System Threat Correlation:
   - Correlate external web request volume with server CPU usage and database connection pool saturation. If all 3 spike simultaneously, trigger Critical DDoS response protocol.""",
            {
                "system": "security",
                "category": "runbook",
                "title": "Cybersecurity Incident Response & Audit Trail Runbook",
                "keywords": "incident response, cybersecurity, audit logs, login events, brute-force response, threat correlation, ddos",
                "source": "security_runbook"
            }
        ),

        # ═════════════════════════════════════════════════════════════════════════
        # CROSS-SYSTEM UNIFIED INTELLIGENCE
        # ═════════════════════════════════════════════════════════════════════════
        (
            """### Unified 3-System Cross-Correlation & Root Cause Analysis Guide
The Enterprise AI RAG Assistant continuously correlates telemetry across all three systems:
1. Database + Server Correlation:
   - If database queries exhibit high latency (>100ms) while server CPU is high (>80%), the root cause is compute resource starvation on the host node rather than database index deficiency.
   - If server CPU is low (<20%) but database queries are slow, the root cause is database-specific (e.g. unindexed table scan, lock contention, or connection pool starvation).
2. Server + Security Correlation:
   - If server CPU spikes suddenly alongside an increase in failed logins or WAF rate-limit blocks (HTTP 429), the root cause is an external brute-force or volumetric application-layer attack.
3. Full 3-System Health Baseline:
   - Database: Buffer cache hit >99%, active connections <20, statement timeout 15s.
   - Server: CPU <40%, RAM <65%, Disk <80%, Load average <4.00 for 8 cores.
   - Security: Threat score 100%, 0 active breaches, 247 firewall rules active, Zero-Trust WAF enforcing.""",
            {
                "system": "all",
                "category": "correlation",
                "title": "Unified 3-System Cross-Correlation & Root Cause Analysis Guide",
                "keywords": "cross-system, root cause analysis, correlation, 3 systems, database server security, holistic diagnostic",
                "source": "unified_correlation"
            }
        ),
    ]
    return corpus


def build_3systems_knowledge_docs() -> list[Document]:
    """Build and chunk all knowledge documents across Database, Server, and Security systems."""
    corpus = get_3systems_knowledge_corpus()
    return chunk_documents(corpus)
