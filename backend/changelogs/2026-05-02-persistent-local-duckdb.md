---
title: Persistent local DuckDB and chat-action label refresh
date: 2026-05-02
version: '0.10.0'
tags: [feature, improvement]
---
All Excel/CSV/Parquet/JSON uploads now share one persistent DuckDB instance per user that survives server restarts and the previous 2-hour session timeout. Each upload becomes a queryable table inside the same DuckDB, so cross-file joins work natively without needing to "append" through a separate UI flow. The chat data-source dropdown collapses these into a single "Local files (N)" entry, and Settings groups them under one "Local files" card with per-table delete and a delete-all option. .duckdb file uploads continue to work as separate read-only data sources. The "Copy response" button is now just "Copy" and "Download CSV" is now "Export CSV". Opus 4.7 sits below Opus 4.6 in the model dropdown.
