# Retrieval Algorithm

CognitiveOS uses semantic search to find relevant memories for context injection.

## Overview

```mermaid
flowchart LR
    Q[User Query] --> E[Embed Query]
    E --> S[Similarity Search]
    S --> F[Filter by Threshold]
    F --> R[Rank by Score]
    R --> C[Format Context]
```

## Embedding Model

**Model:** `all-MiniLM-L6-v2` (Sentence Transformers)

| Property | Value |
|----------|-------|
| Dimensions | 384 |
| Model size | ~90 MB |
| Speed | ~50ms per embedding |
| Quality | Good for short texts |

The model is loaded once as a singleton to avoid repeated initialization.

## Similarity Calculation

### Cosine Similarity

```python
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot_product / (norm_a * norm_b)
```

Score range: -1.0 to 1.0 (typically 0.0 to 1.0 for normalized embeddings)

### Search Process

1. **Query embedding** - Convert user message to 384-dim vector
2. **Candidate retrieval** - All non-deleted nodes with embeddings
3. **Similarity computation** - Cosine similarity for each candidate
4. **Threshold filtering** - Keep only nodes above `SIMILARITY_THRESHOLD`
5. **Top-K selection** - Return highest scoring nodes up to `RETRIEVAL_TOP_K`

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `RETRIEVAL_TOP_K` | 10 | Maximum entities to retrieve |
| `SIMILARITY_THRESHOLD` | 0.7 | Minimum similarity score |

### Tuning Guidelines

**`RETRIEVAL_TOP_K`:**

- **Lower (5-8)**: Focused context, faster, less token usage
- **Higher (15-20)**: Broader context, may include tangential info

**`SIMILARITY_THRESHOLD`:**

- **Lower (0.5-0.6)**: More results, potentially less relevant
- **Higher (0.8-0.9)**: Fewer results, high precision

## Backend-Specific Implementation

### JSON Backend (NetworkX)

```python
def search_similar(self, query_embedding: List[float], top_k: int) -> List[Node]:
    """In-memory similarity search."""
    results = []
    for node_id, data in self.graph.nodes(data=True):
        if data.get('embedding'):
            score = cosine_similarity(query_embedding, data['embedding'])
            if score >= self.similarity_threshold:
                results.append((data, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [Node(**r[0]) for r, _ in results[:top_k]]
```

**Performance:** O(n) where n = number of nodes

### SQLite Backend (sqlite-vec)

```python
def search_similar(self, query_embedding: List[float], top_k: int) -> List[Node]:
    """Vector similarity search using sqlite-vec."""
    cursor = self.conn.execute("""
        SELECT nodes.*, vec_distance_cosine(embedding, ?) as distance
        FROM nodes
        WHERE embedding IS NOT NULL
          AND deleted_at IS NULL
          AND (1 - distance) >= ?
        ORDER BY distance ASC
        LIMIT ?
    """, (serialize_embedding(query_embedding), self.similarity_threshold, top_k))

    return [self._row_to_node(row) for row in cursor.fetchall()]
```

**Performance:** O(log n) with proper indexing (KNN search)

## Context Formatting

Retrieved entities are formatted for LLM context injection:

```python
def format_context(self, entities: List[Node]) -> str:
    """Format retrieved entities as context string."""
    if not entities:
        return "No relevant memories found."

    lines = ["Relevant context from memory:"]
    for entity in entities:
        line = f"- {entity.name} ({entity.label})"
        if entity.description:
            line += f": {entity.description}"
        lines.append(line)

    return "\n".join(lines)
```

**Example output:**
```
Relevant context from memory:
- Alice (Person): AI researcher at Anthropic, specializes in RLHF
- Anthropic (Organization): AI safety company in San Francisco
- RLHF (Concept): Reinforcement Learning from Human Feedback
```

## Performance Considerations

### JSON Backend

| Graph Size | Search Time | Notes |
|------------|-------------|-------|
| 100 nodes | ~5ms | Fast |
| 1,000 nodes | ~50ms | Acceptable |
| 10,000 nodes | ~500ms | Consider SQLite |

### SQLite Backend

| Graph Size | Search Time | Notes |
|------------|-------------|-------|
| 100 nodes | ~10ms | Index overhead |
| 1,000 nodes | ~15ms | Scales well |
| 10,000 nodes | ~30ms | Recommended |
| 100,000 nodes | ~100ms | Production ready |

## Deduplication

During retrieval, entities merged via consolidation are handled:

1. **Soft-deleted nodes** - Filtered out (`deleted_at IS NULL`)
2. **Merged nodes** - Follow `merged_into_id` pointer to primary

## Relevance Boosting

Future enhancement: Boost scores based on:

- **Recency** - Recently updated entities score higher
- **Importance** - High importance entities score higher
- **Access frequency** - Frequently accessed entities score higher

```python
# Potential future implementation
def boosted_score(base_score: float, node: Node) -> float:
    recency_boost = 1.0 / (1 + days_since_update(node))
    importance_boost = node.metadata.importance
    access_boost = min(1.0, node.metadata.access_count / 10)

    return base_score * (1 + 0.1 * recency_boost + 0.1 * importance_boost + 0.1 * access_boost)
```

## Debugging Retrieval

### Enable Debug Logging

```ini
LOG_LEVEL=DEBUG
```

### Check Retrieved Context

In console mode, the retrieved context is logged before response generation:

```
DEBUG: Retrieved context for query "What's my job?"
DEBUG: - Alice (Person): 0.89
DEBUG: - Anthropic (Organization): 0.82
DEBUG: - AI safety (Concept): 0.75
```

### Test Similarity Manually

```python
from src.memory.embeddings import EmbeddingService

es = EmbeddingService.get_instance()
emb1 = es.embed("Python programming")
emb2 = es.embed("coding in Python")
emb3 = es.embed("cooking recipes")

# Should be high
print(cosine_similarity(emb1, emb2))  # ~0.85

# Should be low
print(cosine_similarity(emb1, emb3))  # ~0.15
```

## See Also

- [Architecture Overview](overview.md)
- [Knowledge Graph Schema](knowledge-graph.md)
- [Configuration Reference](../getting-started/configuration.md)
