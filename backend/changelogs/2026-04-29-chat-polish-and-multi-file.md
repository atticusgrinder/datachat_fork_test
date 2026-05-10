---
title: Multi-file uploads, chat polish, and Opus 4.7
date: 2026-04-29
version: '0.9.0'
tags: [feature, improvement]
---
Upload multiple Excel/CSV files into the same DuckDB session and ask questions that join across them. Chat UI gets a batch of polish: prompt whitespace is preserved, the input box collapses back to one line after sending, the page auto-scrolls while a response streams, up arrow inside a multi-line prompt now moves your cursor instead of recalling history (it only recalls when the cursor is on the first line), copy buttons live on every prompt and response, and any query response with results gets a Download CSV button. Demo chat now matches the main chat's terse, no-fluff tone, and Claude Opus 4.7 is selectable in the model picker.
