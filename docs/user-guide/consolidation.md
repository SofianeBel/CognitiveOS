# Memory Consolidation

Consolidation optimizes your knowledge graph by merging duplicates and pruning stale data.

## Overview

Over time, the knowledge graph may accumulate:
- **Duplicate entities** - "Python" and "Python programming"
- **Stale data** - Entities not accessed for months
- **Low-importance nodes** - Rarely referenced entities

Consolidation addresses these issues while preserving history (soft delete).

## Configuration

Set these in your `.env` file:

```ini
# Similarity threshold for duplicate detection
DUPLICATE_MERGE_THRESHOLD=0.9

# Days of inactivity before considering pruning
PRUNE_INACTIVE_DAYS=30

# Max importance score to prune (0.0-1.0)
PRUNE_IMPORTANCE_THRESHOLD=0.3
```

## Running Consolidation

### Programmatic

```python
from src.consolidation.engine import ConsolidationEngine
from src.memory.graph import MemoryGraph

memory = MemoryGraph()
engine = ConsolidationEngine(memory)

# Run full consolidation
result = engine.consolidate()

print(f"Merged: {result['merged']}")
print(f"Pruned: {result['pruned']}")
```

### What Happens

1. **Duplicate Detection**
   - Find entities with similar embeddings
   - Group by entity type
   - Merge into primary entity

2. **Soft Delete**
   - Set `deleted_at` timestamp
   - Set `merged_into_id` pointer
   - Preserve in audit log

3. **Pruning**
   - Find inactive entities (no access in X days)
   - Check importance threshold
   - Soft delete if below threshold

## Viewing Results

### Audit Log (SQLite only)

```python
history = memory.get_audit_history("entity_id")
for entry in history:
    print(f"{entry['timestamp']}: {entry['operation']}")
```

### Merged Entities

```python
merged = memory.get_merged_nodes("primary_entity_id")
for node in merged:
    print(f"Merged: {node.name}")
```

## Undo Consolidation

Soft-deleted nodes can be restored:

```python
# Restore a soft-deleted node
memory.conn.execute("""
    UPDATE nodes
    SET deleted_at = NULL, merged_into_id = NULL
    WHERE id = ?
""", (node_id,))
memory.conn.commit()
```

## Best Practices

1. **Backup first** - Always backup before consolidation
2. **Start conservative** - Use high thresholds initially
3. **Review results** - Check audit log after consolidation
4. **Schedule regularly** - Run weekly or monthly

## Tuning Thresholds

### `DUPLICATE_MERGE_THRESHOLD`

- **0.95** - Very conservative, only near-exact duplicates
- **0.90** - Recommended, catches most duplicates
- **0.85** - Aggressive, may merge distinct entities

### `PRUNE_INACTIVE_DAYS`

- **90** - Conservative, 3 months of inactivity
- **30** - Recommended
- **7** - Aggressive, weekly pruning

### `PRUNE_IMPORTANCE_THRESHOLD`

- **0.2** - Only prune very low importance
- **0.3** - Recommended
- **0.5** - Aggressive, prunes many entities

## Limitations

- **JSON backend** - No soft delete, changes are permanent
- **Undo window** - Soft-deleted data is kept indefinitely (for now)
- **Manual trigger** - No automatic scheduling (Phase 4 planned)

## See Also

- [Architecture Overview](../architecture/overview.md)
- [Storage Backends](../architecture/storage.md)
- [Configuration](../getting-started/configuration.md)
