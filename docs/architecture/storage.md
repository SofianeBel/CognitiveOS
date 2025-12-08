# Storage Backends

CognitiveOS supports two storage backends for the knowledge graph.

## Backend Comparison

| Feature | JSON | SQLite |
|---------|------|--------|
| **Setup** | None | Requires sqlite-vec |
| **File format** | Single .json file | Single .db file |
| **Human readable** | Yes | No |
| **Vector search** | In-memory (O(n)) | Native (O(log n)) |
| **ACID transactions** | No | Yes |
| **Concurrent access** | No | Limited |
| **Soft delete** | No | Yes |
| **Audit logging** | No | Yes |
| **Max recommended size** | ~1,000 nodes | ~100,000+ nodes |

## JSON Backend

### Configuration

```ini
STORAGE_BACKEND=json
MEMORY_FILE=data/memory.json
```

### File Structure

```json
{
  "version": 1,
  "created_at": "2025-01-15T10:00:00Z",
  "nodes": {
    "node_id_1": {
      "id": "node_id_1",
      "label": "Person",
      "name": "Alice",
      "description": "AI researcher",
      "embedding": [0.123, -0.456, ...],
      "metadata": {
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
        "importance": 0.8,
        "access_count": 5
      }
    }
  },
  "edges": [
    {
      "id": "edge_id_1",
      "source": "user",
      "target": "node_id_1",
      "relation": "KNOWS",
      "metadata": {
        "created_at": "2025-01-15T10:00:00Z",
        "confidence": 1.0
      }
    }
  ]
}
```

### Implementation

Uses NetworkX in-memory graph with JSON serialization:

```python
class MemoryGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._load_from_file()

    def save(self):
        data = nx.node_link_data(self.graph)
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)
```

### Pros

- No additional dependencies
- Human-readable for debugging
- Easy to backup (copy file)
- Portable across systems

### Cons

- Loads entire graph to memory
- No vector search optimization
- No transaction support
- No soft delete or audit log

### Best For

- Development and testing
- Small knowledge graphs (<1,000 nodes)
- Quick prototyping
- Debugging

## SQLite Backend

### Configuration

```ini
STORAGE_BACKEND=sqlite
DATABASE_PATH=data/memory.db
```

### Schema

```sql
-- Version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY
);

-- Nodes table with vector support
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    embedding BLOB,  -- sqlite-vec format
    importance REAL DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT NULL,
    merged_into_id TEXT DEFAULT NULL
);

-- Edges table
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation TEXT NOT NULL,
    description TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source) REFERENCES nodes(id),
    FOREIGN KEY (target) REFERENCES nodes(id)
);

-- Audit log for temporal versioning
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    operation TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_name TEXT,
    changes TEXT,  -- JSON
    reason TEXT
);

-- Indexes
CREATE INDEX idx_nodes_label ON nodes(label);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_deleted ON nodes(deleted_at);
CREATE INDEX idx_edges_source ON edges(source);
CREATE INDEX idx_edges_target ON edges(target);
CREATE INDEX idx_audit_entity ON audit_log(entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

### Vector Search with sqlite-vec

```python
def search_similar(self, query_embedding: List[float], top_k: int) -> List[Node]:
    """Native vector similarity search."""
    # Serialize embedding to sqlite-vec format
    query_blob = serialize_embedding(query_embedding)

    cursor = self.conn.execute("""
        SELECT *, vec_distance_cosine(embedding, ?) as distance
        FROM nodes
        WHERE embedding IS NOT NULL
          AND deleted_at IS NULL
        ORDER BY distance ASC
        LIMIT ?
    """, (query_blob, top_k))

    return [self._row_to_node(row) for row in cursor.fetchall()]
```

### Soft Delete

SQLite backend supports soft delete for temporal versioning:

```python
def soft_delete_node(self, node_id: str, merged_into: Optional[str] = None):
    """Soft delete a node, preserving history."""
    self.conn.execute("""
        UPDATE nodes
        SET deleted_at = datetime('now'),
            merged_into_id = ?
        WHERE id = ?
    """, (merged_into, node_id))
```

### Audit Logging

All operations are logged:

```python
def log_audit(self, operation: str, entity_type: str, entity_id: str,
              entity_name: str = None, changes: dict = None, reason: str = None):
    """Log an audit entry."""
    self.conn.execute("""
        INSERT INTO audit_log (operation, entity_type, entity_id, entity_name, changes, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (operation, entity_type, entity_id, entity_name, json.dumps(changes), reason))
```

### Schema Migration

Automatic migration on startup:

```python
def _ensure_schema(self):
    """Create or migrate schema."""
    current_version = self._get_schema_version()

    if current_version < 2:
        self._migrate_to_v2()
        self._set_schema_version(2)

def _migrate_to_v2(self):
    """Add soft-delete columns and audit log."""
    self.conn.execute("ALTER TABLE nodes ADD COLUMN deleted_at TEXT DEFAULT NULL")
    self.conn.execute("ALTER TABLE nodes ADD COLUMN merged_into_id TEXT DEFAULT NULL")
    # Create audit_log table...
```

### Pros

- Native vector search (fast)
- ACID transactions
- Soft delete support
- Audit logging
- Scales to 100K+ nodes
- Single-file database (portable)

### Cons

- Requires sqlite-vec extension
- Windows installation can be tricky
- Not human-readable
- Limited concurrent writes

### Best For

- Production use
- Large knowledge graphs
- Need for audit trail
- Performance-critical applications

## Migration: JSON to SQLite

### Using the Migration Script

```bash
python -m src.memory.migrate --json data/memory.json --db data/memory.db
```

### Migration Process

1. **Backup** - Original JSON file is preserved
2. **Schema creation** - SQLite tables created
3. **Node migration** - All nodes copied with embeddings
4. **Edge migration** - All edges copied
5. **Verification** - Count comparison

### Verification

```bash
# Check node counts match
python -c "
from src.memory.graph import MemoryGraph
import os

os.environ['STORAGE_BACKEND'] = 'json'
json_graph = MemoryGraph()
print(f'JSON nodes: {len(json_graph.get_all_nodes())}')

os.environ['STORAGE_BACKEND'] = 'sqlite'
sqlite_graph = MemoryGraph()
print(f'SQLite nodes: {len(sqlite_graph.get_all_nodes())}')
"
```

## Backup Strategies

### JSON Backup

```bash
cp data/memory.json data/memory.json.backup
```

### SQLite Backup

```bash
# Simple file copy (when not in use)
cp data/memory.db data/memory.db.backup

# Or use SQLite backup command
sqlite3 data/memory.db ".backup data/memory.db.backup"
```

### Automated Backup

```python
import shutil
from datetime import datetime

def backup_memory():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy("data/memory.db", f"data/backups/memory_{timestamp}.db")
```

## See Also

- [Architecture Overview](overview.md)
- [Configuration Reference](../getting-started/configuration.md)
- [Migration Guide](../user-guide/migration.md)
