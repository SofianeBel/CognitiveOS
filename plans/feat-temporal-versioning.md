# feat: Versioning temporel des faits mémoriels (Simplified)

## Overview

Ajouter soft-delete et un audit log simple pour préserver l'historique des modifications sans perdre de données lors des consolidations.

**PRD Reference**: FR-6 "Versioning temporel des faits"

## Problem Statement

1. Les mises à jour de nœuds écrasent les valeurs précédentes
2. Le merge de duplicats supprime définitivement les nœuds secondaires
3. Le pruning supprime les nœuds inactifs sans trace

**Solution simple**: Soft-delete + audit log (pas de bi-temporal modeling, pas de triggers complexes)

## Technical Approach

### 1. Add Soft-Delete Columns (2 fields)

```python
# src/memory/models.py - Add to Node class
class Node(BaseModel):
    # ... existing fields ...
    deleted_at: Optional[datetime] = None      # Soft delete timestamp
    merged_into_id: Optional[str] = None       # Points to survivor node
```

```sql
-- Add to nodes table (database.py)
ALTER TABLE nodes ADD COLUMN deleted_at TEXT DEFAULT NULL;
ALTER TABLE nodes ADD COLUMN merged_into_id TEXT DEFAULT NULL;
```

### 2. Simple Audit Log Table

```sql
-- One table for all history (no triggers)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    operation TEXT NOT NULL,     -- 'create', 'update', 'delete', 'merge'
    entity_type TEXT NOT NULL,   -- 'node', 'edge'
    entity_id TEXT NOT NULL,
    entity_name TEXT,            -- For human readability
    changes TEXT,                -- JSON: what changed
    reason TEXT                  -- Why: 'consolidation', 'user_edit', etc.
);

CREATE INDEX idx_audit_entity ON audit_log(entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

### 3. Update Consolidation Engine

```python
# src/consolidation/engine.py - Modify _execute_merge()

def _execute_merge(self, primary: Node, duplicates: List[Node]) -> None:
    """Merge duplicates using soft-delete (preserves history)."""
    for dup in duplicates:
        # Log the merge
        self.memory.log_audit(
            operation="merge",
            entity_type="node",
            entity_id=dup.id,
            entity_name=dup.name,
            changes={"merged_into": primary.id, "old_name": dup.name},
            reason="duplicate_merge"
        )
        # Soft-delete: mark as merged, don't hard delete
        self.memory.soft_delete_node(dup.id, merged_into=primary.id)
```

### 4. Update Prune Logic

```python
# src/consolidation/engine.py - Modify _prune_inactive()

def _prune_inactive(self, threshold_days: int) -> List[str]:
    """Prune using soft-delete (preserves history)."""
    candidates = self.memory.get_inactive_nodes(threshold_days)
    pruned = []

    for node in candidates:
        self.memory.log_audit(
            operation="delete",
            entity_type="node",
            entity_id=node.id,
            entity_name=node.name,
            reason="prune_inactive"
        )
        self.memory.soft_delete_node(node.id)
        pruned.append(node.name)

    return pruned
```

## Implementation

### File: `src/memory/database.py` additions

```python
# Add to SQLiteMemoryStore class

def soft_delete_node(self, node_id: str, merged_into: Optional[str] = None) -> None:
    """Soft-delete a node instead of removing it."""
    with self._get_connection() as conn:
        conn.execute("""
            UPDATE nodes
            SET deleted_at = datetime('now'),
                merged_into_id = ?
            WHERE id = ?
        """, (merged_into, node_id))
        conn.commit()

def log_audit(
    self,
    operation: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None,
    changes: Optional[dict] = None,
    reason: Optional[str] = None
) -> None:
    """Log an operation to the audit trail."""
    import json
    with self._get_connection() as conn:
        conn.execute("""
            INSERT INTO audit_log (operation, entity_type, entity_id, entity_name, changes, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            operation,
            entity_type,
            entity_id,
            entity_name,
            json.dumps(changes) if changes else None,
            reason
        ))
        conn.commit()

def get_audit_history(self, entity_id: str) -> List[dict]:
    """Get audit history for an entity."""
    import json
    with self._get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM audit_log
            WHERE entity_id = ?
            ORDER BY timestamp DESC
        """, (entity_id,))

        results = []
        for row in cursor.fetchall():
            r = dict(row)
            if r.get('changes'):
                r['changes'] = json.loads(r['changes'])
            results.append(r)
        return results

def get_merged_nodes(self, primary_id: str) -> List[Node]:
    """Get nodes that were merged into a primary node."""
    with self._get_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM nodes
            WHERE merged_into_id = ? AND deleted_at IS NOT NULL
        """, (primary_id,))
        return [self._row_to_node(row) for row in cursor.fetchall()]
```

### Update all queries to exclude soft-deleted

```python
# Add to existing queries
def get_all_nodes(self) -> List[Node]:
    """Get all active nodes."""
    with self._get_connection() as conn:
        cursor = conn.execute(
            "SELECT * FROM nodes WHERE deleted_at IS NULL"  # <-- Add filter
        )
        return [self._row_to_node(row) for row in cursor.fetchall()]
```

## Acceptance Criteria

- [ ] `deleted_at` and `merged_into_id` columns added to nodes table
- [ ] `audit_log` table created
- [ ] `soft_delete_node()` method works
- [ ] `log_audit()` records operations
- [ ] `get_audit_history()` returns history
- [ ] Consolidation uses soft-delete instead of hard delete
- [ ] All queries filter `WHERE deleted_at IS NULL`
- [ ] Schema migration from v1 to v2 works

## What This Does NOT Include (By Design)

| Feature | Why Excluded |
|---------|--------------|
| Bi-temporal modeling | YAGNI - EdgeValidity unused |
| SQLite triggers | Application-level logging is simpler/debuggable |
| `get_node_at_time()` | Not needed for core use case |
| `GraphDiff` | No user-facing feature requires this |
| `TemporalQueryMixin` | Just add methods to existing class |
| Pagination | Local system, won't have 1000+ versions |
| History retention policy | Solve when it's a problem |

## Migration Script

```python
# src/memory/migrate_v2.py

def migrate_to_v2(db_path: str) -> None:
    """Migrate schema from v1 to v2 (add soft-delete + audit log)."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check current version
    cursor.execute("SELECT version FROM schema_version")
    version = cursor.fetchone()[0]

    if version >= 2:
        print("Already on v2")
        return

    print("Migrating v1 -> v2...")

    # Add soft-delete columns
    cursor.execute("ALTER TABLE nodes ADD COLUMN deleted_at TEXT DEFAULT NULL")
    cursor.execute("ALTER TABLE nodes ADD COLUMN merged_into_id TEXT DEFAULT NULL")

    # Create audit log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            operation TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            entity_name TEXT,
            changes TEXT,
            reason TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")

    # Update schema version
    cursor.execute("UPDATE schema_version SET version = 2")

    conn.commit()
    conn.close()
    print("Migration complete!")
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Implementation time | < 2 hours |
| Lines of code added | < 100 |
| Queries to update | ~5-10 (add `WHERE deleted_at IS NULL`) |
| Breaking changes | Zero (soft-delete is additive) |

## Files to Modify

| File | Changes |
|------|---------|
| `src/memory/models.py` | Add `deleted_at`, `merged_into_id` fields |
| `src/memory/database.py` | Add soft-delete methods, audit log, update queries |
| `src/consolidation/engine.py` | Use soft-delete instead of hard delete |
| `src/memory/migrate_v2.py` | New migration script |

## Testing

```python
# tests/test_soft_delete.py

def test_soft_delete_preserves_node():
    store = SQLiteMemoryStore(":memory:")
    node = Node(label="Person", name="Alice")
    store.add_node(node)

    store.soft_delete_node(node.id)

    # Should not appear in normal queries
    assert store.get_node(node.id) is None

    # But data is preserved
    with store._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM nodes WHERE id = ?", (node.id,))
        row = cursor.fetchone()
        assert row is not None
        assert row['deleted_at'] is not None

def test_merge_preserves_history():
    store = SQLiteMemoryStore(":memory:")
    alice = Node(label="Person", name="Alice")
    alice_dup = Node(label="Person", name="Alice Smith")
    store.add_node(alice)
    store.add_node(alice_dup)

    store.soft_delete_node(alice_dup.id, merged_into=alice.id)

    # Original still accessible
    assert store.get_node(alice.id) is not None

    # Merged nodes retrievable
    merged = store.get_merged_nodes(alice.id)
    assert len(merged) == 1
    assert merged[0].name == "Alice Smith"

def test_audit_log():
    store = SQLiteMemoryStore(":memory:")
    node = Node(label="Person", name="Alice")
    store.add_node(node)

    store.log_audit(
        operation="update",
        entity_type="node",
        entity_id=node.id,
        entity_name="Alice",
        changes={"description": "Added job info"}
    )

    history = store.get_audit_history(node.id)
    assert len(history) == 1
    assert history[0]['operation'] == 'update'
```

## References

- DHH Philosophy: "Clarity over cleverness"
- PRD FR-6: "Versioning temporel des faits"
