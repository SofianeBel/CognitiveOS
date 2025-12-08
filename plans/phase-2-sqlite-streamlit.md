# Phase 2: SQLite Persistence & Streamlit UI

**Objective**: Replace in-memory NetworkX with SQLite + sqlite-vec for persistent vector storage, add Streamlit UI with interactive graph visualization.

---

## Overview

Phase 2 transforms CognitiveOS from a prototype into a usable application:
1. **Persistent Storage**: SQLite with sqlite-vec for vector similarity search
2. **Web Interface**: Streamlit app with chat and graph visualization
3. **Migration**: Tool to migrate Phase 1 JSON data to SQLite

---

## Technical Stack Changes

| Component | Phase 1 | Phase 2 |
|-----------|---------|---------|
| Storage | NetworkX + JSON | SQLite + sqlite-vec |
| Frontend | Console (Rich) | Streamlit + PyVis |
| Vector Search | NumPy dot product | sqlite-vec MATCH |

---

## Implementation Tasks

### 2.1 SQLite Database Layer

**File**: `src/memory/database.py`

#### Schema Design

```sql
-- Core tables
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    importance_score REAL DEFAULT 0.5,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES nodes(id),
    target_id TEXT NOT NULL REFERENCES nodes(id),
    relation TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence REAL DEFAULT 1.0,
    valid_from DATE,
    valid_to DATE,
    is_active INTEGER DEFAULT 1
);

-- Vector tables (sqlite-vec)
CREATE VIRTUAL TABLE vec_nodes USING vec0(
    node_id TEXT PRIMARY KEY,
    embedding float[384],
    label TEXT,
    +name TEXT,
    +description TEXT
);

-- Indexes
CREATE INDEX idx_nodes_label ON nodes(label);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
```

#### Tasks

- [ ] Create `SQLiteMemoryStore` class
- [ ] Implement `add_node()` with vector storage
- [ ] Implement `add_edge()` method
- [ ] Implement `search_similar()` using sqlite-vec MATCH
- [ ] Implement `get_node_neighbors()` for graph traversal
- [ ] Add connection pooling and thread safety
- [ ] Implement `get_stats()` method

### 2.2 Migration Tool

**File**: `src/memory/migrate.py`

Migrate JSON data from Phase 1 to SQLite:

```python
def migrate_json_to_sqlite(json_path: str, db_path: str) -> dict:
    """
    Migrate Phase 1 JSON memory to Phase 2 SQLite.

    Returns:
        {"nodes_migrated": int, "edges_migrated": int}
    """
```

#### Tasks

- [ ] Read existing JSON memory file
- [ ] Create SQLite database with schema
- [ ] Insert nodes with embeddings into vec_nodes
- [ ] Insert edges preserving relationships
- [ ] Validate migration with checksums
- [ ] Add CLI command: `python -m src.memory.migrate`

### 2.3 Update MemoryGraph

**File**: `src/memory/graph.py`

Modify `MemoryGraph` to use SQLite backend:

#### Tasks

- [ ] Add `storage_backend` parameter (json/sqlite)
- [ ] Delegate to `SQLiteMemoryStore` when using sqlite
- [ ] Keep NetworkX for graph traversal operations
- [ ] Update `get_context()` to use sqlite-vec search
- [ ] Ensure backward compatibility with JSON

### 2.4 Streamlit Application

**File**: `app.py`

#### UI Components

```
┌─────────────────────────────────────────────────────┐
│  CognitiveOS                              [Stats]   │
├────────────────────────┬────────────────────────────┤
│                        │                            │
│   Memory Graph         │   Chat Interface           │
│   (PyVis)              │                            │
│                        │   You: ...                 │
│   [Interactive]        │   Assistant: ...           │
│   [Zoomable]           │                            │
│   [Clickable nodes]    │   [Send Message]           │
│                        │                            │
├────────────────────────┴────────────────────────────┤
│  Node Types: 🔴 Person  🟢 Concept  🟡 Preference   │
└─────────────────────────────────────────────────────┘
```

#### Tasks

- [ ] Create `app.py` with Streamlit layout
- [ ] Implement chat interface with `st.chat_message`
- [ ] Add PyVis graph visualization in sidebar
- [ ] Color nodes by entity type
- [ ] Show edge labels on hover
- [ ] Add "Refresh Graph" button
- [ ] Display memory statistics
- [ ] Add session state management
- [ ] Implement search/filter for graph

### 2.5 PyVis Graph Rendering

**File**: `src/ui/graph_viz.py`

```python
def render_memory_graph(memory: MemoryGraph) -> str:
    """
    Render memory graph as interactive HTML.

    Returns:
        HTML string for embedding in Streamlit
    """
```

#### Node Colors

| Entity Type | Color |
|-------------|-------|
| Person | #FF6B6B (red) |
| Concept | #4ECDC4 (teal) |
| Preference | #FFE66D (yellow) |
| Location | #95E1D3 (mint) |
| Organization | #F38181 (coral) |
| Event | #AA96DA (purple) |
| Skill | #FCBAD3 (pink) |

#### Tasks

- [ ] Create PyVis Network from memory graph
- [ ] Style nodes by entity type
- [ ] Add hover tooltips with descriptions
- [ ] Enable physics-based layout
- [ ] Add zoom and pan controls
- [ ] Export to HTML for Streamlit embedding

### 2.6 Update Requirements

**File**: `requirements.txt`

```txt
# Add for Phase 2
sqlite-vec>=0.1.0
streamlit>=1.28.0
pyvis>=0.3.0
```

### 2.7 Configuration Updates

**File**: `src/config.py`

```python
class Settings(BaseSettings):
    # Existing...

    # Phase 2
    storage_backend: str = Field("sqlite", env="STORAGE_BACKEND")
    database_path: str = Field("data/memory.db", env="DATABASE_PATH")
    streamlit_port: int = Field(8501, env="STREAMLIT_PORT")
```

---

## File Structure (Phase 2)

```
CognitiveOS/
├── src/
│   ├── memory/
│   │   ├── database.py      # NEW: SQLite storage
│   │   ├── migrate.py       # NEW: JSON→SQLite migration
│   │   ├── graph.py         # MODIFIED: Use SQLite backend
│   │   └── ...
│   └── ui/
│       ├── __init__.py      # NEW
│       └── graph_viz.py     # NEW: PyVis rendering
├── app.py                   # NEW: Streamlit app
└── ...
```

---

## Acceptance Criteria

### Must Have

- [ ] Memory persists in SQLite after restart
- [ ] Semantic search works with sqlite-vec (<100ms for 10K nodes)
- [ ] Streamlit UI displays chat and graph
- [ ] Graph visualization is interactive (zoom, pan, click)
- [ ] Migration tool converts Phase 1 JSON to SQLite
- [ ] Console CLI still works (`python main.py`)

### Should Have

- [ ] Graph updates in real-time after new messages
- [ ] Node filtering by entity type
- [ ] Search box for finding nodes
- [ ] Statistics panel shows node/edge counts

### Could Have

- [ ] Export graph as image
- [ ] Time-based graph filtering
- [ ] Dark mode toggle

---

## Testing Plan

1. **Unit Tests**
   - SQLite CRUD operations
   - Vector similarity search accuracy
   - Migration data integrity

2. **Integration Tests**
   - Full conversation flow with SQLite
   - Graph visualization rendering

3. **Performance Tests**
   - Query latency with 1K, 10K, 100K nodes
   - Memory usage benchmarks

---

## Dependencies

- **sqlite-vec**: Vector similarity extension for SQLite
  - Install: `pip install sqlite-vec`
  - Docs: https://github.com/asg017/sqlite-vec

- **Streamlit**: Web app framework
  - Install: `pip install streamlit`
  - Docs: https://docs.streamlit.io

- **PyVis**: Network graph visualization
  - Install: `pip install pyvis`
  - Docs: https://pyvis.readthedocs.io

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| sqlite-vec installation issues on Windows | High | Fallback to numpy-based similarity |
| Streamlit performance with large graphs | Medium | Limit visible nodes, add pagination |
| Migration data loss | High | Validate before deleting JSON |

---

## Estimated Effort

| Task | Effort |
|------|--------|
| SQLite Database Layer | Medium |
| Migration Tool | Small |
| Streamlit UI | Medium |
| PyVis Integration | Small |
| Testing | Medium |
| **Total** | **~1-2 days** |
