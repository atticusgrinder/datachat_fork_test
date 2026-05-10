"""Pure parsing functions for dbt manifest.json files."""

from typing import Any


def parse_manifest(manifest_json: dict) -> list[dict[str, Any]]:
    """Parse a dbt manifest.json and extract model/source/metric metadata.

    Returns a list of dicts matching ModelMetadata fields.
    """
    results: list[dict[str, Any]] = []

    nodes = manifest_json.get("nodes", {})
    for node_id, node in nodes.items():
        resource_type = node.get("resource_type", "")

        if resource_type == "model":
            results.append(_parse_model(node))
        elif resource_type == "metric":
            results.append(_parse_metric(node))

    sources = manifest_json.get("sources", {})
    for source_id, source_node in sources.items():
        results.append(_parse_source(source_node))

    # Semantic models (dbt 1.6+)
    semantic_models = manifest_json.get("semantic_models", {})
    for sm_id, sm_node in semantic_models.items():
        results.append(_parse_semantic_model(sm_node))

    return results


def _parse_columns(raw_columns: dict) -> list[dict[str, Any]]:
    """Parse column definitions from a dbt node."""
    columns = []
    for col_name, col_info in raw_columns.items():
        columns.append({
            "name": col_name,
            "description": col_info.get("description", ""),
            "data_type": col_info.get("data_type", ""),
            "tests": [t if isinstance(t, str) else list(t.keys())[0] for t in col_info.get("tests", [])],
        })
    return columns


def _parse_model(node: dict) -> dict[str, Any]:
    """Parse a dbt model node."""
    return {
        "metadata_type": "model",
        "name": node.get("name", ""),
        "schema_name": node.get("schema", ""),
        "database": node.get("database", ""),
        "description": node.get("description", ""),
        "columns": _parse_columns(node.get("columns", {})),
        "tags": node.get("tags", []),
        "meta": {
            "materialized": node.get("config", {}).get("materialized", ""),
            **node.get("meta", {}),
        },
        "relationships": {
            "refs": node.get("refs", []),
            "depends_on": node.get("depends_on", {}),
        },
        "raw_definition": {
            "unique_id": node.get("unique_id", ""),
            "path": node.get("path", ""),
            "raw_code": node.get("raw_code", node.get("raw_sql", "")),
        },
    }


def _parse_source(node: dict) -> dict[str, Any]:
    """Parse a dbt source node."""
    return {
        "metadata_type": "source",
        "name": node.get("name", ""),
        "schema_name": node.get("schema", ""),
        "database": node.get("database", ""),
        "description": node.get("description", ""),
        "columns": _parse_columns(node.get("columns", {})),
        "tags": node.get("tags", []),
        "meta": {
            "source_name": node.get("source_name", ""),
            "loader": node.get("loader", ""),
            "freshness": node.get("freshness", {}),
        },
        "relationships": {
            "depends_on": node.get("depends_on", {}),
        },
        "raw_definition": {
            "unique_id": node.get("unique_id", ""),
            "identifier": node.get("identifier", ""),
        },
    }


def _parse_metric(node: dict) -> dict[str, Any]:
    """Parse a dbt metric node."""
    return {
        "metadata_type": "metric",
        "name": node.get("name", ""),
        "schema_name": node.get("schema", ""),
        "database": node.get("database", ""),
        "description": node.get("description", ""),
        "columns": [],
        "tags": node.get("tags", []),
        "meta": {
            "type": node.get("type", ""),
            "label": node.get("label", ""),
            "calculation_method": node.get("calculation_method", ""),
            "expression": node.get("expression", ""),
        },
        "relationships": {
            "depends_on": node.get("depends_on", {}),
        },
        "raw_definition": {
            "unique_id": node.get("unique_id", ""),
        },
    }


def _parse_semantic_model(node: dict) -> dict[str, Any]:
    """Parse a dbt semantic model node (dbt 1.6+)."""
    return {
        "metadata_type": "metric",
        "name": node.get("name", ""),
        "schema_name": node.get("schema", ""),
        "database": node.get("database", ""),
        "description": node.get("description", ""),
        "columns": [],
        "tags": node.get("tags", []),
        "meta": {
            "model": node.get("model", ""),
            "entities": node.get("entities", []),
            "measures": node.get("measures", []),
            "dimensions": node.get("dimensions", []),
        },
        "relationships": {
            "depends_on": node.get("depends_on", {}),
        },
        "raw_definition": {
            "unique_id": node.get("unique_id", ""),
        },
    }
