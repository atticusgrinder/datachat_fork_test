"""Tool definitions and dispatch for warehouse operations."""

import re
from typing import Optional, Tuple, List

from app.connections.base import WarehouseExecutor

_WRITE_KEYWORDS_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b", re.IGNORECASE
)

TOOL_DEFINITIONS = [
    {
        "name": "execute_sql",
        "description": "Execute a SQL query against the connected data warehouse and return formatted results. Use this for any data retrieval or analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SQL query to execute.",
                }
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_datasets",
        "description": "List all databases or datasets available in the connected warehouse. Use this to discover what data is available.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_tables",
        "description": "List all tables in a specific dataset or database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "The dataset or database name to list tables from.",
                }
            },
            "required": ["dataset"],
        },
    },
    {
        "name": "get_table_schema",
        "description": "Get the column names, data types, and other schema information for a specific table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dataset": {
                    "type": "string",
                    "description": "The dataset or database name containing the table.",
                },
                "table": {
                    "type": "string",
                    "description": "The table name to get the schema for.",
                },
            },
            "required": ["dataset", "table"],
        },
    },
]


FILE_TOOL_DEFINITIONS = [
    {
        "name": "execute_query",
        "description": "Execute a SQL query against the user's uploaded data using DuckDB and return formatted results. Use DuckDB SQL dialect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The DuckDB SQL query to execute.",
                }
            },
            "required": ["sql"],
        },
    },
]

_WRITE_KEYWORDS_FILE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b", re.IGNORECASE
)


async def execute_file_tool(
    executor,
    tool_name: str,
    tool_input: dict,
) -> Tuple[str, bool]:
    """Dispatch a file tool call. Returns (result_text, is_error)."""
    try:
        if tool_name == "execute_query":
            sql = tool_input.get("sql", "")
            if _WRITE_KEYWORDS_FILE_RE.search(sql):
                return (
                    "Error: Write operations are not permitted on uploaded data. "
                    "Only SELECT queries are allowed.",
                    True,
                )
            result = await executor.execute_sql(sql)
            return result, False
        else:
            return f"Unknown tool: {tool_name}", True
    except Exception as e:
        return f"Error: {e}", True


async def execute_tool(
    executor: WarehouseExecutor,
    tool_name: str,
    tool_input: dict,
    allowed_tables: Optional[List[str]] = None,
) -> Tuple[str, bool]:
    """Dispatch a tool call to the appropriate executor method.

    Returns (result_text, is_error).
    """
    try:
        if tool_name == "execute_sql":
            sql = tool_input["sql"]
            if allowed_tables is not None and _WRITE_KEYWORDS_RE.search(sql):
                return (
                    "Error: Write operations (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE) "
                    "are not permitted when a table allowlist is active.",
                    True,
                )
            result = await executor.execute_sql(sql)
        elif tool_name == "list_datasets":
            result = await executor.list_datasets()
        elif tool_name == "list_tables":
            result = await executor.list_tables(tool_input["dataset"])
        elif tool_name == "get_table_schema":
            result = await executor.get_table_schema(
                tool_input["dataset"], tool_input["table"]
            )
        else:
            return f"Unknown tool: {tool_name}", True

        return result, False
    except Exception as e:
        return f"Error: {e}", True
