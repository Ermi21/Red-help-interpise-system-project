import pytest

from app.database.readonly_guard import check_connection_level_safety, enforce_row_limit, is_safe, validate_sql
from app.utils.exceptions import UnsafeSQLError


class TestSafeStatementsAllowed:
    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM customers",
            "select id, name from Orders where status = 'open'",
            "SHOW TABLES",
            "EXPLAIN SELECT * FROM customers",
            "DESCRIBE customers",
            "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent",
        ],
    )
    def test_allows_safe_statements(self, sql):
        assert is_safe(sql) is True
        assert validate_sql(sql)  # does not raise


class TestUnsafeStatementsRejected:
    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO customers (name) VALUES ('x')",
            "UPDATE customers SET name = 'x'",
            "DELETE FROM customers",
            "DROP TABLE customers",
            "ALTER TABLE customers ADD COLUMN x TEXT",
            "TRUNCATE customers",
            "CREATE TABLE x (id INT)",
            "GRANT ALL ON customers TO someone",
            "SELECT * INTO backup_customers FROM customers",
            "CALL some_procedure()",
        ],
    )
    def test_rejects_unsafe_statements(self, sql):
        assert is_safe(sql) is False
        with pytest.raises(UnsafeSQLError):
            validate_sql(sql)


class TestInjectionPatterns:
    def test_rejects_stacked_queries(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("SELECT * FROM customers; DROP TABLE customers;")

    def test_rejects_comment_smuggled_write(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("SELECT * FROM customers WHERE 1=1; -- DROP TABLE customers")

    def test_rejects_empty_statement(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("   ")


class TestRowLimitEnforcement:
    def test_adds_limit_when_missing(self):
        result = enforce_row_limit("SELECT * FROM customers", max_rows=100)
        assert "LIMIT 100" in result

    def test_leaves_existing_limit_untouched(self):
        result = enforce_row_limit("SELECT * FROM customers LIMIT 10", max_rows=100)
        assert result.count("LIMIT") == 1
        assert "LIMIT 10" in result


class TestConnectionLevelSafetyCheck:
    """Regression tests for the permissive engine-level check.

    check_connection_level_safety is deliberately more lenient than
    validate_sql: it must NOT block SQLAlchemy's own internal reflection
    queries (e.g. SQLite's `PRAGMA table_info(...)`, used by the Inspector
    during schema discovery), while still catching real mutations.
    """

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT * FROM customers",
            'PRAGMA table_info("customers")',
            "PRAGMA main.table_xinfo(customers)",
            "SHOW TABLES",
        ],
    )
    def test_allows_reflection_and_read_statements(self, sql):
        check_connection_level_safety(sql)  # should not raise

    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO customers (name) VALUES ('x')",
            "UPDATE customers SET name = 'x'",
            "DELETE FROM customers",
            "DROP TABLE customers",
            "ALTER TABLE customers ADD COLUMN x TEXT",
            "SELECT * INTO backup_customers FROM customers",
        ],
    )
    def test_still_blocks_real_mutations(self, sql):
        with pytest.raises(UnsafeSQLError):
            check_connection_level_safety(sql)
