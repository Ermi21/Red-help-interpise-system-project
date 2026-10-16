import pytest

from app.chatbot.sql_safety import extract_sql, validate_llm_sql
from app.utils.exceptions import UnsafeSQLError


class TestExtractSql:
    def test_strips_markdown_fence(self):
        llm_output = "```sql\nSELECT * FROM customers\n```"
        assert extract_sql(llm_output) == "SELECT * FROM customers"

    def test_handles_plain_sql(self):
        assert extract_sql("SELECT * FROM customers") == "SELECT * FROM customers"

    def test_strips_trailing_semicolon(self):
        assert extract_sql("SELECT 1;") == "SELECT 1"


class TestValidateLlmSql:
    def test_accepts_valid_select(self):
        assert validate_llm_sql("```sql\nSELECT COUNT(*) FROM customers\n```") == "SELECT COUNT(*) FROM customers"

    def test_rejects_write_even_if_fenced(self):
        with pytest.raises(UnsafeSQLError):
            validate_llm_sql("```sql\nDELETE FROM customers\n```")

    def test_rejects_empty_output(self):
        with pytest.raises(UnsafeSQLError):
            validate_llm_sql("")

    def test_rejects_non_sql_hallucination(self):
        with pytest.raises(UnsafeSQLError):
            validate_llm_sql("I'm sorry, I cannot answer that.")
