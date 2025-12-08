# MemoryGraph

The main interface for knowledge graph operations.

**Module:** `src.memory.graph`

## Class Definition

```python
class MemoryGraph:
    """
    Knowledge graph for storing entities and relationships.

    Supports two storage backends:
    - JSON: NetworkX graph serialized to JSON file
    - SQLite: SQLite database with sqlite-vec for vector search

    The backend is selected via STORAGE_BACKEND environment variable.
    """
```

## Constructor

```python
def __init__(self, file_path: Optional[str] = None):
    """
    Initialize the memory graph.

    Args:
        file_path: Optional path override for storage file.
                   Defaults to MEMORY_FILE or DATABASE_PATH env vars.

    Environment Variables:
        STORAGE_BACKEND: "json" or "sqlite" (default: "json")
        MEMORY_FILE: Path for JSON storage (default: "data/memory.json")
        DATABASE_PATH: Path for SQLite storage (default: "data/memory.db")
    """
```

### Example

```python
from src.memory.graph import MemoryGraph

# Use environment defaults
memory = MemoryGraph()

# Override file path
memory = MemoryGraph(file_path="custom/path/memory.db")
```

## Methods

### add_node

```python
def add_node(self, node: Node) -> None:
    """
    Add a node to the graph.

    If a node with the same ID exists, it will be updated.
    Embeddings are generated automatically if not provided.

    Args:
        node: Node object to add.

    Raises:
        ValueError: If node validation fails.
    """
```

#### Example

```python
from src.memory.models import Node

node = Node(
    label="Person",
    name="Alice",
    description="AI researcher at Anthropic"
)
memory.add_node(node)
```

### add_edge

```python
def add_edge(self, edge: Edge) -> None:
    """
    Add an edge (relationship) between two nodes.

    Both source and target nodes must exist.

    Args:
        edge: Edge object to add.

    Raises:
        ValueError: If source or target node doesn't exist.
    """
```

#### Example

```python
from src.memory.models import Edge

edge = Edge(
    source="alice_123",
    target="anthropic_456",
    relation="WORKS_AT"
)
memory.add_edge(edge)
```

### get_node

```python
def get_node(self, node_id: str) -> Optional[Node]:
    """
    Retrieve a node by ID.

    Args:
        node_id: Unique node identifier.

    Returns:
        Node object if found, None otherwise.
        Soft-deleted nodes are excluded (SQLite backend).
    """
```

#### Example

```python
node = memory.get_node("alice_123")
if node:
    print(f"Found: {node.name}")
```

### get_node_by_name

```python
def get_node_by_name(self, name: str, label: Optional[str] = None) -> Optional[Node]:
    """
    Find a node by name (and optionally label).

    Args:
        name: Node display name (case-insensitive).
        label: Optional entity type filter.

    Returns:
        First matching node, or None if not found.
    """
```

#### Example

```python
alice = memory.get_node_by_name("Alice", label="Person")
```

### get_all_nodes

```python
def get_all_nodes(self) -> List[Node]:
    """
    Get all nodes in the graph.

    Returns:
        List of all non-deleted nodes.
    """
```

### search_similar

```python
def search_similar(
    self,
    query: str,
    top_k: int = 10,
    threshold: float = 0.7
) -> List[Tuple[Node, float]]:
    """
    Search for semantically similar nodes.

    Args:
        query: Natural language search query.
        top_k: Maximum results to return.
        threshold: Minimum similarity score (0.0-1.0).

    Returns:
        List of (node, similarity_score) tuples, sorted by score descending.
    """
```

#### Example

```python
results = memory.search_similar("AI safety research", top_k=5)
for node, score in results:
    print(f"{node.name}: {score:.2f}")
```

### get_neighbors

```python
def get_neighbors(
    self,
    node_id: str,
    relation: Optional[str] = None,
    direction: str = "both"
) -> List[Node]:
    """
    Get neighboring nodes connected by edges.

    Args:
        node_id: Source node ID.
        relation: Filter by relation type (e.g., "WORKS_AT").
        direction: "outgoing", "incoming", or "both".

    Returns:
        List of connected nodes.
    """
```

#### Example

```python
# Get all connections
neighbors = memory.get_neighbors("alice_123")

# Get only workplaces
workplaces = memory.get_neighbors("alice_123", relation="WORKS_AT", direction="outgoing")
```

### get_edges

```python
def get_edges(
    self,
    node_id: Optional[str] = None,
    relation: Optional[str] = None
) -> List[Edge]:
    """
    Get edges, optionally filtered.

    Args:
        node_id: Filter by source or target node.
        relation: Filter by relation type.

    Returns:
        List of matching edges.
    """
```

### delete_node

```python
def delete_node(self, node_id: str) -> bool:
    """
    Delete a node and its connected edges.

    JSON backend: Hard delete
    SQLite backend: Soft delete (sets deleted_at)

    Args:
        node_id: Node to delete.

    Returns:
        True if deleted, False if not found.
    """
```

### get_stats

```python
def get_stats(self) -> Dict[str, Any]:
    """
    Get graph statistics.

    Returns:
        Dictionary with:
        - nodes: Total node count (excluding soft-deleted)
        - edges: Total edge count
        - storage: Backend type ("json" or "sqlite")
        - file_path: Storage file path
    """
```

#### Example

```python
stats = memory.get_stats()
print(f"Nodes: {stats['nodes']}")
print(f"Edges: {stats['edges']}")
print(f"Storage: {stats['storage']}")
```

### save

```python
def save(self) -> None:
    """
    Persist changes to storage.

    JSON backend: Writes to file immediately.
    SQLite backend: Commits transaction.

    Called automatically after add/delete operations.
    """
```

## Properties

### nodes_data

```python
@property
def nodes_data(self) -> Dict[str, Dict]:
    """
    Raw node data dictionary.

    Returns:
        Dictionary mapping node_id to node data.

    Note:
        For advanced use cases. Prefer using methods above.
    """
```

### edges_data

```python
@property
def edges_data(self) -> List[Dict]:
    """
    Raw edge data list.

    Returns:
        List of edge dictionaries.
    """
```

## SQLite-Specific Methods

Available only when using SQLite backend (`STORAGE_BACKEND=sqlite`):

### soft_delete_node

```python
def soft_delete_node(self, node_id: str, merged_into: Optional[str] = None) -> None:
    """
    Soft delete a node, preserving history.

    Args:
        node_id: Node to soft-delete.
        merged_into: If merging, ID of the primary node.
    """
```

### log_audit

```python
def log_audit(
    self,
    operation: str,
    entity_type: str,
    entity_id: str,
    entity_name: Optional[str] = None,
    changes: Optional[Dict] = None,
    reason: Optional[str] = None
) -> None:
    """
    Log an audit entry.

    Args:
        operation: "create", "update", "delete", "merge", "prune"
        entity_type: "node" or "edge"
        entity_id: Affected entity ID
        entity_name: Human-readable name
        changes: Dictionary of changes (serialized as JSON)
        reason: Reason for the operation
    """
```

### get_audit_history

```python
def get_audit_history(self, entity_id: str) -> List[Dict]:
    """
    Get audit log entries for an entity.

    Args:
        entity_id: Entity to get history for.

    Returns:
        List of audit entries, newest first.
    """
```

### get_merged_nodes

```python
def get_merged_nodes(self, primary_id: str) -> List[Node]:
    """
    Get nodes that were merged into a primary node.

    Args:
        primary_id: Primary/surviving node ID.

    Returns:
        List of soft-deleted nodes with merged_into_id = primary_id.
    """
```

## Full Example

```python
from src.memory.graph import MemoryGraph
from src.memory.models import Node, Edge

# Initialize
memory = MemoryGraph()

# Add entities
alice = Node(label="Person", name="Alice", description="AI researcher")
anthropic = Node(label="Organization", name="Anthropic")

memory.add_node(alice)
memory.add_node(anthropic)

# Add relationship
works_at = Edge(
    source=alice.id,
    target=anthropic.id,
    relation="WORKS_AT"
)
memory.add_edge(works_at)

# Search
results = memory.search_similar("AI companies")
print(f"Found {len(results)} results")

# Get stats
stats = memory.get_stats()
print(f"Graph has {stats['nodes']} nodes and {stats['edges']} edges")
```

## See Also

- [Node Model](models.md#node)
- [Edge Model](models.md#edge)
- [Storage Backends](../architecture/storage.md)
- [Configuration](../getting-started/configuration.md)
