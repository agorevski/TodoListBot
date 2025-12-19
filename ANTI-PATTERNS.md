# Development Anti-Patterns Found

This document lists development anti-patterns identified in the TodoListBot codebase.

---

## 1. **Database Connection Not Using Context Manager Consistently**

**Location:** `src/todo_bot/storage/sqlite.py`

**Issue:** The `TaskStorage` base class implements `__aenter__` and `__aexit__` for context manager support, but the actual usage in `bot.py` doesn't use it:

```python
# In bot.py - doesn't use context manager
self.storage = SQLiteTaskStorage(db_path=db_path)
# Later manually calls initialize() and close()
```

**Why it's bad:** The context manager pattern is defined but not used, which could lead to resource leaks if `close()` isn't called.

**Recommendation:** Use `async with storage:` pattern or remove the unused context manager methods.

---

## 2. **No Input Validation in Storage Layer**

**Location:** `src/todo_bot/storage/sqlite.py`

**Issue:** The storage layer accepts data without validation. Validation happens in the cog layer, but if storage is used directly, invalid data could be stored.

```python
async def add_task(
    self,
    description: str,  # No length validation
    priority: Priority,
    # ...
) -> Task:
```

**Why it's bad:** Violates defense in depth. If the storage is called from a different entry point, validation could be bypassed.

**Recommendation:** Add validation in the storage layer or use validated types that enforce constraints.

---

## 3. **Rollover Task Potential N+1 Query Problem**

**Location:** `src/todo_bot/storage/sqlite.py` (lines 586-683)

**Issue:** The `rollover_incomplete_tasks` method performs a SELECT query for each task to check for duplicates:

```python
for task_row in incomplete_tasks:
    # ... 
    cursor = await conn.execute(  # Query inside loop
        "SELECT id FROM tasks WHERE ..."
    )
```

**Why it's bad:** This is an N+1 query pattern. For N incomplete tasks, it performs N+1 database queries.

**Recommendation:** Fetch all existing tasks for the target date in a single query, then check membership in Python.

---

## Summary

| Severity | Count | Categories |
|----------|-------|------------|
| Medium | 3 | N+1 queries, unused context managers, missing validation |

