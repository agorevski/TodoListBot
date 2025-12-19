# Development Anti-Patterns Found

This document lists development anti-patterns identified in the TodoListBot codebase.

---

## 2. **Type: ignore Comments Without Explanation**

**Location:** `src/todo_bot/views/task_view.py` (line 291)

**Issue:** Using `# type: ignore` without explaining why the type check is being suppressed.

```python
await interaction.message.edit(  # type: ignore
    content=self.get_content(),
    view=self,
)
```

**Why it's bad:** Makes it unclear whether this is hiding a real bug or a known limitation of the type system.

**Recommendation:** Add a comment explaining why the type ignore is necessary, e.g., `# type: ignore[union-attr]  # message is always present after button callback`

---

## 3. **Singleton Pattern with Class-Level Mutable State**

**Location:** `src/todo_bot/main.py` (lines 15-40)

**Issue:** The `CleanupManager` uses a class-level `_instance` variable for singleton pattern with mutable state.

```python
class CleanupManager:
    _instance: "CleanupManager | None" = None
    _lock: threading.Lock = threading.Lock()
```

**Why it's bad:** Class-level mutable state can cause issues in testing and makes the code harder to reason about. The `_lock` is created at class definition time, which is unusual.

**Recommendation:** Consider using a module-level singleton or dependency injection pattern instead.

---

## 4. **Unused Imported Exception Types**

**Location:** `src/todo_bot/exceptions.py`

**Issue:** The `ValidationError` and `ConfigurationError` exceptions are defined but rarely or never used in the actual codebase. Instead, bare `ValueError` is raised in many places.

**Why it's bad:** Defines custom exceptions but doesn't use them consistently, making exception handling less precise.

**Recommendation:** Either use the custom exceptions consistently or remove unused ones.

---

## 5. **Magic Numbers in UI Constants**

**Location:** `src/todo_bot/config.py` (lines 11-17)

**Issue:** While constants are defined, they're scattered and some lack clear documentation about their purpose.

```python
RATE_LIMIT_COMMANDS: Final[int] = 5
RATE_LIMIT_SECONDS: Final[float] = 10.0
VIEW_TIMEOUT_SECONDS: Final[float] = 300.0
MAX_BUTTONS_PER_VIEW: Final[int] = 25
BUTTONS_PER_ROW: Final[int] = 5
```

**Why it's bad:** The relationship between constants (e.g., why 5 buttons per row with max 25 total = 5 rows) isn't documented, making it harder to understand Discord's limitations.

**Recommendation:** Add docstrings or comments explaining the rationale (e.g., "Discord limits views to 5 rows × 5 buttons = 25 max").

---

## 6. **Inconsistent Error Response Handling**

**Location:** `src/todo_bot/cogs/tasks.py`

**Issue:** Some error responses use `ephemeral=True` while success responses are mixed. The pattern isn't consistent.

```python
# Error - ephemeral
await interaction.response.send_message(ErrorMessages.GUILD_ONLY, ephemeral=True)

# Success - not ephemeral
await interaction.response.send_message(format_task_done(task))

# Success - ephemeral
await interaction.response.send_message(format_task_added(task), ephemeral=True)
```

**Why it's bad:** Inconsistent UX - some success messages are visible to all, others only to the user.

**Recommendation:** Document and standardize when responses should be ephemeral.

---

## 7. **Database Connection Not Using Context Manager Consistently**

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

## 8. **No Input Validation in Storage Layer**

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

## 9. **Rollover Task Potential N+1 Query Problem**

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
| High | 1 | Security (secrets in .env) |
| Medium | 3 | N+1 queries, unused context managers, missing validation |
| Low | 5 | Style inconsistencies, missing documentation |

