# API Reference

This section documents the public API of CognitiveOS.

## Core Classes

| Class | Module | Description |
|-------|--------|-------------|
| [CognitiveLoop](cognitive-loop.md) | `src.graph_loop` | Main conversation orchestrator |
| [MemoryGraph](memory-graph.md) | `src.memory.graph` | Knowledge graph interface |
| [ExtractionAgent](../architecture/overview.md#extractionagent) | `src.agents.extractor` | Entity extraction |
| [EmbeddingService](../architecture/overview.md#embeddingservice) | `src.memory.embeddings` | Text embeddings |
| [ConsolidationEngine](../user-guide/consolidation.md) | `src.consolidation.engine` | Memory optimization |

## Data Models

| Model | Module | Description |
|-------|--------|-------------|
| [Node](models.md#node) | `src.memory.models` | Graph node/entity |
| [Edge](models.md#edge) | `src.memory.models` | Graph edge/relation |
| [NodeMetadata](models.md#nodemetadata) | `src.memory.models` | Node metadata |
| [EntityExtraction](models.md#entityextraction) | `src.agents.extractor` | Extraction result |

## Quick Start

### Basic Usage

```python
from src.graph_loop import CognitiveLoop

# Initialize
loop = CognitiveLoop()

# Have a conversation
response = loop.invoke("Hi, I'm Alice and I work at Anthropic.")
print(response)

# Check memory stats
stats = loop.memory.get_stats()
print(f"Nodes: {stats['nodes']}, Edges: {stats['edges']}")
```

### Direct Memory Access

```python
from src.memory.graph import MemoryGraph
from src.memory.models import Node

# Create memory graph
memory = MemoryGraph()

# Add a node
node = Node(
    label="Person",
    name="Alice",
    description="AI researcher"
)
memory.add_node(node)

# Search for similar entities
results = memory.search_similar(
    query="Who is Alice?",
    top_k=5
)
```

### Using Embeddings

```python
from src.memory.embeddings import EmbeddingService

# Get singleton instance
service = EmbeddingService.get_instance()

# Generate embedding
vector = service.embed("Python programming")
print(f"Dimensions: {len(vector)}")  # 384
```

## Configuration

All classes respect environment variables:

```ini
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai
STORAGE_BACKEND=sqlite
DATABASE_PATH=data/memory.db
```

See [Configuration Reference](../getting-started/configuration.md) for all options.

## Error Handling

```python
from src.graph_loop import CognitiveLoop

try:
    loop = CognitiveLoop()
    response = loop.invoke("Hello")
except ValueError as e:
    print(f"Configuration error: {e}")
except ConnectionError as e:
    print(f"LLM connection error: {e}")
```

## Thread Safety

- `EmbeddingService` - Thread-safe singleton
- `MemoryGraph` - NOT thread-safe, use separate instances per thread
- `CognitiveLoop` - NOT thread-safe, use separate instances per thread

For async applications, use thread pool executors:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def chat_async(message: str) -> str:
    loop = asyncio.get_event_loop()
    cognitive_loop = CognitiveLoop()  # Create per-request
    return await loop.run_in_executor(
        executor,
        cognitive_loop.invoke,
        message
    )
```

## Versioning

API follows [Semantic Versioning](https://semver.org/):

- **v0.x.x** - Development phase, breaking changes possible
- **v1.x.x** - Stable API (planned)

Current version: **v0.3.0**
