"""Native Salesforce executor — queries Salesforce via REST API.

Replaces the MCP bridge approach with direct API calls for reliability.
"""

import json
import logging
from typing import Any, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

SFDC_API_VERSION = "v60.0"


SALESFORCE_TOOL_DEFINITIONS = [
    {
        "name": "salesforce_query",
        "description": "Execute a SOQL query against Salesforce and return the results. Use this for any data retrieval.",
        "input_schema": {
            "type": "object",
            "properties": {
                "soql": {
                    "type": "string",
                    "description": "The SOQL query to execute, e.g. SELECT Id, Name FROM Account LIMIT 10",
                }
            },
            "required": ["soql"],
        },
    },
    {
        "name": "salesforce_list_objects",
        "description": "List all available Salesforce objects (sObjects) that can be queried.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "salesforce_describe_object",
        "description": "Get the fields, data types, and relationships for a Salesforce object.",
        "input_schema": {
            "type": "object",
            "properties": {
                "object_name": {
                    "type": "string",
                    "description": "The API name of the Salesforce object, e.g. Account, Contact, Opportunity",
                }
            },
            "required": ["object_name"],
        },
    },
]


class SalesforceExecutor:
    """Executes queries and metadata lookups against Salesforce REST API."""

    def __init__(self, instance_url: str, access_token: str):
        self.instance_url = instance_url.rstrip("/")
        self.access_token = access_token
        self._base_url = f"{self.instance_url}/services/data/{SFDC_API_VERSION}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def query(self, soql: str) -> str:
        """Execute a SOQL query and return formatted results."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/query/",
                params={"q": soql},
                headers=self._headers(),
            )
            if resp.status_code != 200:
                error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"message": resp.text}
                msg = error[0].get("message", resp.text) if isinstance(error, list) else error.get("message", resp.text)
                return f"SOQL Error: {msg}"

            data = resp.json()
            records = data.get("records", [])
            total = data.get("totalSize", 0)

            if not records:
                return f"Query returned 0 records."

            # Format as a readable table
            # Remove 'attributes' key from each record
            clean_records = []
            for r in records:
                clean = {k: v for k, v in r.items() if k != "attributes"}
                clean_records.append(clean)

            columns = list(clean_records[0].keys())
            lines = [" | ".join(columns)]
            lines.append(" | ".join(["---"] * len(columns)))
            for rec in clean_records:
                row = []
                for col in columns:
                    val = rec.get(col)
                    if isinstance(val, dict):
                        val = val.get("Name") or val.get("Id") or json.dumps(val)
                    row.append(str(val) if val is not None else "")
                lines.append(" | ".join(row))

            result = "\n".join(lines)
            if total > len(records):
                result += f"\n\n(Showing {len(records)} of {total} total records)"
            return result

    async def list_objects(self) -> str:
        """List queryable Salesforce objects."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/sobjects/",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return f"Error listing objects: {resp.text}"

            data = resp.json()
            objects = [
                obj for obj in data.get("sobjects", [])
                if obj.get("queryable", False)
            ]
            objects.sort(key=lambda o: o["name"])

            lines = ["Name | Label | Custom"]
            lines.append("--- | --- | ---")
            for obj in objects:
                custom = "Yes" if obj.get("custom", False) else ""
                lines.append(f"{obj['name']} | {obj.get('label', '')} | {custom}")

            return f"{len(objects)} queryable objects:\n\n" + "\n".join(lines)

    async def describe_object(self, object_name: str) -> str:
        """Describe a Salesforce object's fields."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self._base_url}/sobjects/{object_name}/describe/",
                headers=self._headers(),
            )
            if resp.status_code == 404:
                return f"Object '{object_name}' not found."
            if resp.status_code != 200:
                return f"Error describing {object_name}: {resp.text}"

            data = resp.json()
            fields = data.get("fields", [])

            lines = [f"**{data.get('label', object_name)}** ({object_name}) — {len(fields)} fields\n"]
            lines.append("Field | Label | Type | Reference To")
            lines.append("--- | --- | --- | ---")
            for f in fields:
                ref = ", ".join(f.get("referenceTo", [])) if f.get("referenceTo") else ""
                lines.append(f"{f['name']} | {f.get('label', '')} | {f['type']} | {ref}")

            return "\n".join(lines)


async def execute_salesforce_tool(
    executor: SalesforceExecutor,
    tool_name: str,
    tool_input: dict,
    allowed_objects: Optional[List[str]] = None,
) -> Tuple[str, bool]:
    """Dispatch a Salesforce tool call.

    Returns (result_text, is_error).
    """
    try:
        if tool_name == "salesforce_query":
            soql = tool_input["soql"]
            # Enforce allowed objects if set
            if allowed_objects:
                soql_upper = soql.upper()
                from_idx = soql_upper.find("FROM")
                if from_idx != -1:
                    after_from = soql[from_idx + 4:].strip().split()[0] if len(soql) > from_idx + 4 else ""
                    obj_name = after_from.strip().rstrip(",;)")
                    if obj_name and obj_name not in allowed_objects:
                        return f"Error: Querying '{obj_name}' is not allowed. Permitted objects: {', '.join(allowed_objects)}", True
            result = await executor.query(soql)
        elif tool_name == "salesforce_list_objects":
            result = await executor.list_objects()
        elif tool_name == "salesforce_describe_object":
            result = await executor.describe_object(tool_input["object_name"])
        else:
            return f"Unknown tool: {tool_name}", True

        return result, False
    except Exception as e:
        return f"Error: {e}", True
