import ast, pathlib, sys

BASE = pathlib.Path(__file__).parent
FILES = [
    "app/main.py",
    "app/models/notification.py",
    "app/models/system_metrics.py",
    "app/models/login_event.py",
    "app/models/audit_log.py",
    "app/models/llm_usage.py",
    "app/models/__init__.py",
    "app/core/event_bus.py",
    "app/workers/metrics_collector.py",
    "app/workers/alert_evaluator.py",
    "app/api/v1/ws.py",
    "app/api/v1/notifications_api.py",
    "app/api/v1/server_detail.py",
    "app/api/v1/security_detail.py",
    "app/api/v1/router.py",
    "app/api/v1/auth.py",
    "app/chatbot/rag_pipeline.py",
]

ok = True
for rel in FILES:
    p = BASE / rel
    if not p.exists():
        print(f"MISSING  {rel}")
        ok = False
        continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"OK       {rel}")
    except SyntaxError as e:
        print(f"ERR      {rel}  ->  {e}")
        ok = False

sys.exit(0 if ok else 1)
