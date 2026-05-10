---
title: Reports page polish and local-file scheduled reports
date: 2026-05-06
version: '0.11.0'
tags: [feature, improvement]
---
The Reports page is cleaner: scheduled reports render as single-line rows with inline rename, the report detail view gains expand / show-data / refresh icons on each visualization, and the embedded chat panel was removed. Pie charts on small cards no longer get their labels clipped. Scheduled email reports also work for chats backed by uploaded files (local DuckDB), not just warehouses, and each email now renders an actual chart shape — colored bars or a stacked-bar legend for pie — with a lowercase subject and no duplicate header for single-viz reports.
