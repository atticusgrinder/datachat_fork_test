"""Base warehouse executor interface."""

import logging
from abc import ABC, abstractmethod
from collections import OrderedDict

from tabulate import tabulate

logger = logging.getLogger("warehouse_executor")

MAX_ROWS = 500
MAX_CHARS = 50000
MAX_SCHEMA_TABLES = 50
MAX_SCHEMA_COLUMNS_PER_TABLE = 30


def format_schema_summary(rows: list[tuple], database: str) -> str:
    """Format (schema, table, column, type) tuples into a compact schema summary."""
    tables: OrderedDict[str, list[str]] = OrderedDict()
    for schema_name, table_name, column_name, col_type in rows:
        key = f"{database}.{schema_name}.{table_name}"
        if key not in tables:
            if len(tables) >= MAX_SCHEMA_TABLES:
                break
            tables[key] = []
        if len(tables[key]) < MAX_SCHEMA_COLUMNS_PER_TABLE:
            tables[key].append(f"{column_name} ({col_type})")

    truncated = len(tables) >= MAX_SCHEMA_TABLES
    lines = [f"{key}: {', '.join(cols)}" for key, cols in tables.items()]
    summary = "\n".join(lines)

    if truncated:
        summary += (
            "\n\n-- Schema truncated. Use list_datasets, list_tables, "
            "and get_table_schema tools for full discovery."
        )

    return summary


class WarehouseExecutor(ABC):
    """Base class for warehouse executors."""

    async def connect(self) -> None:
        """Pre-warm the connection."""

    async def get_schema_summary(self) -> str:
        """Return a compact schema summary for prompt injection."""
        return ""

    async def verify_read_only(self) -> bool:
        """Attempt a write operation to verify the connection is read-only."""
        raise NotImplementedError

    @abstractmethod
    async def execute_sql(self, sql: str) -> str:
        """Execute a SQL query and return formatted results."""

    @abstractmethod
    async def list_datasets(self) -> str:
        """List all databases/datasets."""

    @abstractmethod
    async def list_tables(self, dataset: str) -> str:
        """List tables in a dataset/schema."""

    @abstractmethod
    async def get_table_schema(self, dataset: str, table: str) -> str:
        """Get column names and types for a table."""
