"""Pure parsing functions for Omni repo YAML files.

Omni stores its semantic model definitions as YAML files, typically with
extensions like `.view`, `.model`, and `.topic`. This module walks a repo
tree, loads each recognized file, and normalizes the contents into the same
dict shape that the dbt parser emits so the downstream formatting and
context-storage code can stay uniform across integration types.
"""

from pathlib import Path
from typing import Any

import yaml

OMNI_EXTENSIONS = {".view", ".model", ".topic"}
OMNI_YAML_DIRS = {"views", "models", "topics"}


def parse_repo(repo_root: Path) -> list[dict[str, Any]]:
    """Walk an Omni repo and extract metadata for every view/model/topic file."""
    results: list[dict[str, Any]] = []

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if not _is_omni_file(path):
            continue

        try:
            with open(path, "r") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError:
            continue

        if not isinstance(raw, dict):
            continue

        kind = _classify(path)
        if kind == "view":
            results.append(_parse_view(raw, path))
        elif kind == "model":
            results.append(_parse_model(raw, path))
        elif kind == "topic":
            results.append(_parse_topic(raw, path))

    return results


def _is_omni_file(path: Path) -> bool:
    if path.suffix in OMNI_EXTENSIONS:
        return True
    if path.suffix in {".yml", ".yaml"}:
        return any(part in OMNI_YAML_DIRS for part in path.parts)
    return False


def _classify(path: Path) -> str:
    if path.suffix == ".view" or "views" in path.parts:
        return "view"
    if path.suffix == ".model" or "models" in path.parts:
        return "model"
    if path.suffix == ".topic" or "topics" in path.parts:
        return "topic"
    return "view"


def _parse_view(node: dict, path: Path) -> dict[str, Any]:
    dimensions = node.get("dimensions", []) or []
    measures = node.get("measures", []) or []
    columns = [_parse_field(f, "dimension") for f in dimensions] + [
        _parse_field(f, "measure") for f in measures
    ]
    return {
        "metadata_type": "view",
        "name": node.get("name", path.stem),
        "schema_name": node.get("schema", ""),
        "database": node.get("database", ""),
        "description": node.get("description", "") or node.get("label", ""),
        "columns": columns,
        "tags": node.get("tags", []) or [],
        "meta": {
            "table_name": node.get("table_name", ""),
            "sql_table_name": node.get("sql_table_name", ""),
            "connection": node.get("connection", ""),
        },
        "relationships": {},
        "raw_definition": {
            "path": str(path.name),
        },
    }


def _parse_model(node: dict, path: Path) -> dict[str, Any]:
    return {
        "metadata_type": "model",
        "name": node.get("name", path.stem),
        "schema_name": "",
        "database": "",
        "description": node.get("description", "") or node.get("label", ""),
        "columns": [],
        "tags": node.get("tags", []) or [],
        "meta": {
            "connection": node.get("connection", ""),
            "views": node.get("views", []) or [],
        },
        "relationships": {},
        "raw_definition": {
            "path": str(path.name),
        },
    }


def _parse_topic(node: dict, path: Path) -> dict[str, Any]:
    return {
        "metadata_type": "topic",
        "name": node.get("name", path.stem),
        "schema_name": "",
        "database": "",
        "description": node.get("description", "") or node.get("label", ""),
        "columns": [],
        "tags": node.get("tags", []) or [],
        "meta": {
            "base_view": node.get("base_view", ""),
            "joins": node.get("joins", []) or [],
        },
        "relationships": {},
        "raw_definition": {
            "path": str(path.name),
        },
    }


def _parse_field(field: Any, field_kind: str) -> dict[str, Any]:
    if not isinstance(field, dict):
        return {"name": str(field), "description": "", "data_type": "", "tests": []}
    return {
        "name": field.get("name", ""),
        "description": field.get("description", "") or field.get("label", ""),
        "data_type": field.get("type", "") or field.get("aggregate_type", ""),
        "tests": [],
        "kind": field_kind,
    }
