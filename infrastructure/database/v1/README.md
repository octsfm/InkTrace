# V1.1 Workbench Database Namespace

This directory is reserved for V1.1 Workbench database infrastructure.

Stage 0 scope:

- database connection baseline
- migration baseline
- V1.1 model namespace
- SQLite WAL, busy timeout, and foreign key baseline
- `works`, `chapters`, and `edit_sessions` empty table migration baseline
- integer `version` fields with default `1` for later optimistic locking

Out of scope for this directory during Stage 0:

- Works business logic
- Chapters business logic
- structured asset business logic
- Legacy data migration
