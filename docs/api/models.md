# Data Models

Pydantic models used throughout CognitiveOS.

**Module:** `src.memory.models`

## Node

Represents an entity in the knowledge graph.

```python
class Node(BaseModel):
    """A node in the memory graph representing an entity."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str                              # Entity type
    name: str                               # Display name
    description: Optional[str] = None       # Human-readable description
    embedding: Optional[List[float]] = None # 384-dim vector
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)

    # Soft-delete fields (SQLite only)
    deleted_at: Optional[datetime] = None
    merged_into_id: Optional[str] = None
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Auto | UUID v4 identifier |
| `label` | str | Yes | Entity type (Person, Concept, etc.) |
| `name` | str | Yes | Display name |
| `description` | str | No | Human-readable description |
| `embedding` | List[float] | No | 384-dim embedding vector |
| `metadata` | NodeMetadata | Auto | Timestamps and metrics |
| `deleted_at` | datetime | No | Soft-delete timestamp |
| `merged_into_id` | str | No | Primary node if merged |

### Example

```python
from src.memory.models import Node

# Minimal node
node = Node(label="Person", name="Alice")

# Full node
node = Node(
    label="Person",
    name="Alice",
    description="AI researcher at Anthropic",
    embedding=[0.1, 0.2, ...],  # 384 values
    metadata=NodeMetadata(importance=0.8)
)
```

### Entity Types

| Label | Description |
|-------|-------------|
| `Person` | Named individuals |
| `Concept` | Abstract ideas |
| `Preference` | Likes/dislikes |
| `Skill` | Abilities |
| `Location` | Places |
| `Event` | Occurrences |
| `Organization` | Companies/groups |

---

## NodeMetadata

Metadata for graph nodes.

```python
class NodeMetadata(BaseModel):
    """Metadata for a graph node."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = Field(default=0, ge=0)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `created_at` | datetime | now | Creation timestamp |
| `updated_at` | datetime | now | Last update timestamp |
| `importance` | float | 0.5 | Importance score (0.0-1.0) |
| `access_count` | int | 0 | Retrieval count |

### Example

```python
from src.memory.models import NodeMetadata

metadata = NodeMetadata(
    importance=0.9,
    access_count=5
)
```

---

## Edge

Represents a relationship between two nodes.

```python
class Edge(BaseModel):
    """An edge in the memory graph representing a relationship."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str                             # Source node ID
    target: str                             # Target node ID
    relation: str                           # Relationship type
    description: Optional[str] = None       # Context
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata)
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | str | Auto | UUID v4 identifier |
| `source` | str | Yes | Source node ID |
| `target` | str | Yes | Target node ID |
| `relation` | str | Yes | Relationship type |
| `description` | str | No | Additional context |
| `metadata` | EdgeMetadata | Auto | Timestamps |

### Example

```python
from src.memory.models import Edge

edge = Edge(
    source="alice_123",
    target="anthropic_456",
    relation="WORKS_AT",
    description="AI safety research position"
)
```

### Relation Types

| Relation | Description |
|----------|-------------|
| `KNOWS` | Personal connection |
| `WORKS_AT` | Employment |
| `LIVES_IN` | Residence |
| `LIKES` | Positive preference |
| `DISLIKES` | Negative preference |
| `LEARNED` | Skill acquisition |
| `INTERESTED_IN` | Topic interest |
| `ATTENDED` | Event participation |
| `BELONGS_TO` | Membership |
| `CREATED` | Creation/authorship |
| `RELATED_TO` | General relationship |

---

## EdgeMetadata

Metadata for graph edges.

```python
class EdgeMetadata(BaseModel):
    """Metadata for a graph edge."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `created_at` | datetime | now | Creation timestamp |
| `confidence` | float | 1.0 | Extraction confidence (0.0-1.0) |

---

## ExtractedEntity

Entity extracted from conversation text.

**Module:** `src.agents.extractor`

```python
class ExtractedEntity(BaseModel):
    """An entity extracted from conversation."""

    name: str                    # Entity name
    label: str                   # Entity type
    description: Optional[str]   # Description from context
```

### Example

```python
# From LLM structured output
entity = ExtractedEntity(
    name="Alice",
    label="Person",
    description="Works at Anthropic on AI safety"
)
```

---

## ExtractedRelation

Relationship extracted from conversation text.

```python
class ExtractedRelation(BaseModel):
    """A relation extracted from conversation."""

    source: str       # Source entity name
    target: str       # Target entity name
    relation: str     # Relationship type
```

### Example

```python
relation = ExtractedRelation(
    source="Alice",
    target="Anthropic",
    relation="WORKS_AT"
)
```

---

## EntityExtraction

Complete extraction result from a conversation turn.

```python
class EntityExtraction(BaseModel):
    """Complete extraction result."""

    entities: List[ExtractedEntity]
    relations: List[ExtractedRelation]
```

### Example

```python
extraction = EntityExtraction(
    entities=[
        ExtractedEntity(name="Alice", label="Person"),
        ExtractedEntity(name="Anthropic", label="Organization")
    ],
    relations=[
        ExtractedRelation(source="Alice", target="Anthropic", relation="WORKS_AT")
    ]
)
```

---

## Serialization

All models support Pydantic serialization:

```python
# To dictionary
data = node.model_dump()

# To JSON string
json_str = node.model_dump_json()

# From dictionary
node = Node.model_validate(data)

# From JSON string
node = Node.model_validate_json(json_str)
```

### Excluding Fields

```python
# Exclude embedding for API responses
data = node.model_dump(exclude={"embedding"})

# Include only specific fields
data = node.model_dump(include={"id", "name", "label"})
```

---

## Validation

Models validate data on creation:

```python
# This will raise ValidationError
node = Node(label="Person", name="")  # name cannot be empty

# Importance must be 0.0-1.0
metadata = NodeMetadata(importance=1.5)  # ValidationError
```

---

## See Also

- [MemoryGraph](memory-graph.md)
- [Knowledge Graph Schema](../architecture/knowledge-graph.md)
- [Pydantic Documentation](https://docs.pydantic.dev/)
