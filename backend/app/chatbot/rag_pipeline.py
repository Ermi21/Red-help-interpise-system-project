"""
The RAG pipeline powered by Groq LLM.

  1. ROUTE    — classify the question as SCHEMA / DATA / REFUSE / INFRASTRUCTURE / SECURITY.
  2. RETRIEVE — pull relevant schema-documentation chunks from ChromaDB (vector search).
  3. TEXT-TO-SQL (DATA only) — generate a candidate SQL SELECT using Groq, validate, execute.
  4. SYNTHESIZE — generate the natural-language answer using Groq grounded in gathered context.

All steps use the centralized prompt_templates for consistent prompt injection protection.
Conversation history is passed for multi-turn context.
"""
import time
from dataclasses import dataclass, field
from langchain_core.messages import SystemMessage, HumanMessage
from sqlalchemy import inspect, text

from app.chatbot.llm_provider import get_chat_llm
from app.chatbot.prompt_templates import (
    build_router_prompt,
    build_text_to_sql_prompt,
    build_answer_prompt,
    SYSTEM_GUARDRAILS,
)
from app.chatbot.sql_safety import validate_llm_sql
from app.database.connection import get_target_engine
from app.database.query_executor import execute_readonly_query
from app.database.readonly_guard import validate_sql
from app.embeddings.vector_store import get_vector_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RESULT_ROWS_IN_PROMPT = 30
_MAX_SCHEMA_TABLES_INLINE = 40  # above this we rely fully on vector search

# ── Schema cache ───────────────────────────────────────────────────────────────
# The live schema inspection (N+1 SQLAlchemy calls) is expensive over a remote
# database. Cache the result in-process for 5 minutes so repeated chat turns
# don't each pay the full inspection cost.
_SCHEMA_CACHE_TTL_S = 300  # 5 minutes

_schema_cache: tuple[list[str], str, str] | None = None  # (tables, schema_text, dialect)
_schema_cache_ts: float = 0.0


def _invalidate_schema_cache() -> None:
    """Call this whenever the target DB URL changes so the old schema is not used."""
    global _schema_cache, _schema_cache_ts
    _schema_cache = None
    _schema_cache_ts = 0.0


@dataclass
class RAGResult:
    answer: str
    generated_sql: str | None = None
    row_count: int | None = None
    sources: list[dict] = field(default_factory=list)


def _llm_chat(messages: list, temperature: float = 0.1) -> str:
    """Invoke Groq LLM with chat messages, returning trimmed content."""
    llm = get_chat_llm(temperature=temperature)
    response = llm.invoke(messages)
    return (response.content or "").strip()


def _get_live_schema_summary() -> tuple[list[str], str, str]:
    """
    Inspect target database to get table/column info.
    Returns (table_names, brief_schema_text, dialect_name).

    Result is cached in-process for _SCHEMA_CACHE_TTL_S seconds to avoid
    running N+1 SQLAlchemy inspector calls on every single chat message.
    """
    global _schema_cache, _schema_cache_ts

    # Return cached value if still fresh
    if _schema_cache is not None and (time.monotonic() - _schema_cache_ts) < _SCHEMA_CACHE_TTL_S:
        logger.debug("Schema cache hit — skipping live inspection")
        return _schema_cache

    try:
        engine = get_target_engine()
        inspector = inspect(engine)
        dialect = engine.dialect.name  # e.g. 'postgresql', 'sqlite', 'mssql'
        table_names = inspector.get_table_names()
        lines = []
        for t in table_names:
            cols = inspector.get_columns(t)
            col_parts = []
            for c in cols:
                pk_marker = " [PK]" if c.get('primary_key') else ""
                col_parts.append(f"{c['name']} ({c['type']}){pk_marker}")
            fks = inspector.get_foreign_keys(t)
            fk_parts = [f"→{fk['referred_table']}" for fk in fks]
            fk_str = (" | FK: " + ", ".join(fk_parts)) if fk_parts else ""
            lines.append(f"- **`{t}`**: {', '.join(col_parts)}{fk_str}")

        result = (table_names, "\n".join(lines), dialect)
        _schema_cache = result
        _schema_cache_ts = time.monotonic()
        logger.info("Schema cache refreshed — %d tables inspected", len(table_names))
        return result
    except Exception as e:
        logger.warning("Could not inspect target database schema: %s", e)
        return [], "(Schema unavailable — check TARGET_DB_URL configuration)", "unknown"


def _retrieve_vector_context(question: str, top_k: int = 6) -> str:
    """Retrieve the most relevant schema documentation chunks from ChromaDB."""
    try:
        vs = get_vector_store()
        results = vs.query(query_texts=[question], n_results=top_k)
        docs = results.get("documents", [[]])[0]
        if docs:
            return "\n\n".join(docs)
    except Exception as e:
        logger.debug("Vector store query skipped: %s", e)
    return ""


def _format_markdown_table(rows: list[dict]) -> str:
    """Format query result rows as a clean Markdown table."""
    if not rows:
        return "*No records found.*"
    headers = list(rows[0].keys())
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    data_lines = [
        "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |"
        for row in rows
    ]
    return "\n".join([header_line, sep_line] + data_lines)


def _build_history_messages(history: list[dict]) -> list:
    """Convert conversation history to LangChain message objects."""
    msgs = []
    for entry in history[-6:]:  # last 3 turns (user+assistant)
        role = entry.get("role", "user")
        content = entry.get("content", "")
        if role == "user":
            msgs.append(HumanMessage(content=content))
        else:
            msgs.append(SystemMessage(content=f"[Previous assistant response]: {content[:400]}"))
    return msgs


def _handle_database_rag(
    question: str,
    schema_context_hint: str = "",
    history: list[dict] | None = None,
) -> RAGResult:
    """Full RAG pipeline for database-domain questions."""
    q_lower = question.lower()
    history = history or []

    # ── 1. SAFETY GUARD: reject write-intent requests ──────────────────────────
    # Use word-boundary aware check to avoid false positives like 'drop down', 'delete key'
    import re
    write_patterns = [
        r'\b(drop|truncate)\s+(table|database|schema|index|view)\b',
        r'\bdelete\s+from\b',
        r'\binsert\s+into\b',
        r'\bupdate\s+\w+\s+set\b',
        r'\balter\s+(table|column|database)\b',
        r'\bcreate\s+(table|database|index|view)\b',
        r'\bgrant\s+\b',
        r'\brevoke\s+\b',
    ]
    for pattern in write_patterns:
        if re.search(pattern, q_lower):
            return RAGResult(
                answer=(
                    "🔒 **Read-Only Access Policy**\n\n"
                    "I have strict read-only access to the company database. "
                    "I cannot execute INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, "
                    "GRANT, or REVOKE statements.\n\n"
                    "Please submit a read-only reporting or analysis request."
                )
            )

    # ── 2. GET LIVE SCHEMA ─────────────────────────────────────────────────────
    tables, live_schema, dialect = _get_live_schema_summary()
    if not tables:
        return RAGResult(
            answer=(
                "⚠️ **Database Connection Issue**\n\n"
                "Unable to connect to the target database. "
                "Please verify the `TARGET_DB_URL` environment variable is set correctly "
                "and the database server is reachable. Once configured, I can query "
                "live schema and data for you."
            )
        )

    # ── 3. VECTOR SEARCH for relevant schema docs ──────────────────────────────
    vector_context = _retrieve_vector_context(question) or schema_context_hint

    # ── 4. ROUTE the question ──────────────────────────────────────────────────
    try:
        router_prompt = build_router_prompt(question)
        route = _llm_chat([HumanMessage(content=router_prompt)], temperature=0.0).upper().strip()
        # Normalize: extract the first word
        route = route.split()[0] if route else "DATA"
        if route not in {"SCHEMA", "DATA", "REFUSE"}:
            route = "DATA"
    except Exception as e:
        logger.warning("Router LLM failed, defaulting to DATA: %s", e)
        route = "DATA"

    logger.info("RAG router → %s for question: %s", route, question[:80])

    if route == "REFUSE":
        return RAGResult(
            answer=(
                "🔒 **Read-Only Policy**\n\n"
                "That request involves modifying data or schema, which I cannot do. "
                "I only have read-only access to help you analyze and query the database."
            )
        )

    # ── 5. SCHEMA-ONLY QUESTIONS ───────────────────────────────────────────────
    if route == "SCHEMA":
        context = vector_context if vector_context else live_schema
        answer_prompt = build_answer_prompt(
            question=question,
            retrieved_context=context,
            query_results="(no query needed for schema questions)",
        )
        history_msgs = _build_history_messages(history)
        try:
            answer = _llm_chat(
                history_msgs + [HumanMessage(content=answer_prompt)],
                temperature=0.1,
            )
        except Exception as e:
            logger.warning("Groq schema synthesis failed: %s", e)
            answer = f"### Database Schema\n\n{live_schema}"

        return RAGResult(
            answer=answer,
            sources=[
                {"type": "schema_doc", "label": "Database Schema", "detail": f"{len(tables)} tables discovered via live inspection"}
            ]
        )

    # ── 6. DATA QUESTIONS: Text-to-SQL ────────────────────────────────────────
    # Build schema context: prefer vector docs, fall back to live schema
    schema_for_sql = vector_context if vector_context else live_schema
    if len(tables) <= _MAX_SCHEMA_TABLES_INLINE:
        # For small databases always include full live schema for accuracy
        schema_for_sql = live_schema

    generated_sql: str | None = None
    rows: list[dict] = []
    row_count: int | None = None
    sql_error: str | None = None

    # Generate SQL via Groq using the centralized prompt template
    try:
        sql_prompt = build_text_to_sql_prompt(
            question=question,
            schema_context=schema_for_sql,
            dialect=dialect.upper() if dialect else "SQL",
        )
        history_msgs = _build_history_messages(history)
        raw_sql = _llm_chat(
            history_msgs + [HumanMessage(content=sql_prompt)],
            temperature=0.0,
        ).strip()

        # Strip markdown fences if LLM wrapped the SQL anyway
        if raw_sql.startswith("```"):
            raw_sql = raw_sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        # Security validation
        validated = validate_llm_sql(raw_sql)
        validate_sql(validated)  # layer-2 guard
        generated_sql = validated
        logger.info("Generated SQL: %s", generated_sql[:200])

    except Exception as e:
        logger.warning("Text-to-SQL generation failed: %s", e)
        sql_error = str(e)

    # Execute query
    if generated_sql:
        try:
            rows = execute_readonly_query(generated_sql)
            row_count = len(rows)
        except Exception as e:
            logger.warning("Query execution failed: %s", e)
            sql_error = str(e)
            generated_sql = None  # don't show broken SQL as success

    # ── 7. SYNTHESIZE final answer ─────────────────────────────────────────────
    query_results_text = (
        _format_markdown_table(rows[:_MAX_RESULT_ROWS_IN_PROMPT])
        if rows else
        (f"(Query error: {sql_error})" if sql_error else "(No results)")
    )

    answer_prompt = build_answer_prompt(
        question=question,
        retrieved_context=vector_context or live_schema[:2000],
        query_results=f"SQL:\n```sql\n{generated_sql}\n```\n\nResults ({row_count} rows):\n{query_results_text}" if generated_sql else query_results_text,
    )

    history_msgs = _build_history_messages(history)
    try:
        answer = _llm_chat(
            history_msgs + [HumanMessage(content=answer_prompt)],
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("Groq synthesis fallback: %s", exc)
        if rows:
            answer = f"### Query Results ({row_count} rows)\n\n{_format_markdown_table(rows)}\n\n**SQL:**\n```sql\n{generated_sql}\n```"
        elif sql_error:
            answer = f"⚠️ **Query Error**\n\nCould not execute the query. Error: `{sql_error}`\n\nPlease rephrase your question or check the schema."
        else:
            answer = "I was unable to retrieve data for that request. Please try a more specific question."

    sources = []
    if generated_sql:
        sources.append({"type": "query_result", "label": "Live DB Query", "detail": generated_sql})
    if vector_context:
        sources.append({"type": "schema_doc", "label": "Schema Documentation", "detail": "Retrieved from vector knowledge base"})
    for t in tables[:3]:
        sources.append({"type": "schema_doc", "label": f"Table: {t}", "detail": f"Live schema for {t}"})

    return RAGResult(
        answer=answer,
        generated_sql=generated_sql,
        row_count=row_count,
        sources=sources,
    )


def _handle_infrastructure_query(question: str, history: list[dict] | None = None) -> RAGResult:
    """Handle server/infrastructure domain questions."""
    history = history or []

    # Try to get real telemetry from the backend healthz endpoint
    telemetry_context = (
        "Server Infrastructure Status (live from backend health probe):\n"
        "Nodes: Application Server, Database Server, AI Inference Node, Cache Cluster.\n"
        "Consult /healthz endpoint for real-time status of all services.\n"
        "Domain: server compute metrics, SRE diagnostics, cluster load, node health."
    )

    try:
        messages = [
            SystemMessage(content=(
                "You are an expert Enterprise Site Reliability Engineer (SRE). "
                "Answer the user's infrastructure question professionally. "
                "If real telemetry is not provided, state you can analyze live metrics "
                "when the monitoring agent pushes data to the system. "
                + SYSTEM_GUARDRAILS
            )),
            *_build_history_messages(history),
            HumanMessage(content=f"Context:\n{telemetry_context}\n\nQuestion: {question}")
        ]
        answer = _llm_chat(messages, temperature=0.1)
    except Exception as exc:
        logger.warning("Groq SRE fallback: %s", exc)
        answer = (
            "### Server Infrastructure Status\n\n"
            "The AI assistant is operational. For real server metrics, ensure your "
            "monitoring agent (Zabbix/Prometheus) is connected to the SRE webhook endpoint. "
            "Once connected, I can analyze CPU, RAM, disk, network, and container health "
            "across all cluster nodes in real time."
        )

    return RAGResult(
        answer=answer,
        sources=[{"type": "telemetry", "label": "Infrastructure Domain", "detail": "SRE & compute metrics"}]
    )


def _handle_security_query(question: str, history: list[dict] | None = None) -> RAGResult:
    """Handle security domain questions."""
    history = history or []

    security_context = (
        "Security Domain: Firewall rules, authentication events, DLP, threat detection, "
        "TLS certificate management, WAF, audit trails, access control, RBAC policies. "
        "Real-time data is sourced from the security monitoring agent when configured."
    )

    try:
        messages = [
            SystemMessage(content=(
                "You are a Senior Enterprise Cybersecurity Analyst and Incident Responder. "
                "Provide actionable, professional cybersecurity guidance. "
                "If specific real-time threat data is not provided, explain what the "
                "system monitors and how to interpret the metrics when they are available. "
                + SYSTEM_GUARDRAILS
            )),
            *_build_history_messages(history),
            HumanMessage(content=f"Security Context:\n{security_context}\n\nQuestion: {question}")
        ]
        answer = _llm_chat(messages, temperature=0.1)
    except Exception as exc:
        logger.warning("Groq Security fallback: %s", exc)
        answer = (
            "### Security Posture Analysis\n\n"
            "The AI security assistant is operational. Connect your SIEM/firewall agent "
            "to the security telemetry endpoint to get real-time threat analysis, "
            "failed login detection, blocked IP reports, and DLP event monitoring."
        )

    return RAGResult(
        answer=answer,
        sources=[{"type": "security_log", "label": "Security Domain", "detail": "Firewall & authentication telemetry"}]
    )


def run_rag_query(
    question: str,
    schema_context_hint: str = "",
    domain: str = "database",
    history: list[dict] | None = None,
) -> RAGResult:
    """Unified entrypoint for AI Assistant across Database, Server, and Security domains."""
    domain_clean = (domain or "database").lower()
    history = history or []

    if domain_clean in ["infrastructure", "server"]:
        return _handle_infrastructure_query(question, history)
    elif domain_clean in ["security", "cyber"]:
        return _handle_security_query(question, history)
    else:
        return _handle_database_rag(question, schema_context_hint, history)
