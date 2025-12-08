# Migration Guide

Migrate your data from JSON to SQLite storage.

## Why Migrate?

| Feature | JSON | SQLite |
|---------|------|--------|
| Vector search | In-memory | Native (fast) |
| Scale | ~1,000 nodes | 100,000+ nodes |
| Soft delete | No | Yes |
| Audit logging | No | Yes |

## Before You Start

### 1. Backup Your Data

```bash
cp data/memory.json data/memory.json.backup
```

### 2. Check Current State

```bash
python -c "
import json
data = json.load(open('data/memory.json'))
print(f'Nodes: {len(data.get(\"nodes\", {}))}')
print(f'Edges: {len(data.get(\"edges\", []))}')
"
```

## Migration Process

### Using the Migration Script

```bash
python -m src.memory.migrate --json data/memory.json --db data/memory.db
```

Output:
```
Migrating from data/memory.json to data/memory.db...
Migrating 45 nodes...
Migrating 38 edges...
Migration complete!
Nodes: 45 -> 45 ✓
Edges: 38 -> 38 ✓
```

### Update Configuration

Edit `.env`:
```ini
STORAGE_BACKEND=sqlite
DATABASE_PATH=data/memory.db
```

## Verification

### Check Node Counts

```bash
python -c "
import os
os.environ['STORAGE_BACKEND'] = 'sqlite'
from src.memory.graph import MemoryGraph
m = MemoryGraph()
stats = m.get_stats()
print(f'Nodes: {stats[\"nodes\"]}')
print(f'Edges: {stats[\"edges\"]}')
"
```

### Test Retrieval

```bash
python main.py
# Try: "What do you know about me?"
```

## Troubleshooting

### Migration Fails

**"JSON file not found":**
```bash
ls data/memory.json
# If missing, start fresh with SQLite
```

**"Invalid JSON":**
```bash
python -c "import json; json.load(open('data/memory.json'))"
# Fix syntax errors in the file
```

### Rollback

If migration fails, restore from backup:
```bash
cp data/memory.json.backup data/memory.json
```

And set:
```ini
STORAGE_BACKEND=json
```

## See Also

- [Storage Backends](../architecture/storage.md)
- [Configuration](../getting-started/configuration.md)
