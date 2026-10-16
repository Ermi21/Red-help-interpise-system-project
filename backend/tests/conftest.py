"""
Test env vars are set here, in conftest.py, because it is imported by
pytest before any test module — several app modules (e.g. app.utils.logger)
call get_settings() at import time via module-level logger initialization,
so required settings must exist before the first `import app...` anywhere
in the test suite.
"""
import os

os.environ.setdefault("TARGET_DB_URL", "postgresql+psycopg2://test:test@localhost:5432/target_test")
os.environ.setdefault("APP_DB_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("LOG_DIR", "/tmp/rag_backend_test_logs")
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/rag_backend_test_vector_db")
