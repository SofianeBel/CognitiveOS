# Phase 3 Research: Memory Consolidation & Local LLM Support

**Research Date:** 2025-12-08
**Status:** Complete
**Target Version:** v0.3.0

This document contains comprehensive research on implementing Phase 3 features for CognitiveOS: Memory Consolidation and Local LLM Support with Ollama.

---

## Table of Contents

1. [Memory Consolidation ("Sleep" Process)](#1-memory-consolidation-sleep-process)
2. [Local LLM Support (Ollama)](#2-local-llm-support-ollama)
3. [Implementation Recommendations](#3-implementation-recommendations)
4. [References](#4-references)

---

## 1. Memory Consolidation ("Sleep" Process)

### 1.1 Overview

Memory consolidation in AI agents draws inspiration from neuroscience, where sleep facilitates the transformation of short-term memories into long-term storage through processes of compression, deduplication, and pruning. For knowledge graphs, this involves:

- **Deduplication**: Merging redundant or similar nodes/edges
- **Summarization**: Compressing related memories into higher-level concepts
- **Pruning**: Removing low-importance or outdated information
- **Temporal Decay**: Reducing confidence/relevance scores over time

### 1.2 Key Academic and Industry Frameworks

#### Graphiti (Zep AI)

**Architecture**: Temporal knowledge graph engine built on Neo4j
**GitHub**: https://github.com/getzep/graphiti
**Key Innovation**: Bi-temporal model tracking both event occurrence time and ingestion time

**Core Features**:
- Real-time incremental updates (no batch recomputation)
- Automatic entity extraction and deduplication
- Temporal conflict resolution with validity intervals
- Hybrid retrieval (semantic + keyword + graph traversal)
- P95 latency of 300ms for retrieval

**Deduplication Approach**:
```python
# Edge deduplication constraint
# Only compare edges between SAME entity pairs
# Significantly reduces computational complexity

# Pseudocode from Graphiti paper
def deduplicate_edge(new_edge, existing_edges):
    # Constrain search to edges between same entities
    candidate_edges = [e for e in existing_edges
                      if e.source == new_edge.source
                      and e.target == new_edge.target]

    # Hybrid search: semantic + keyword
    similar_edges = hybrid_search(new_edge, candidate_edges)

    if similar_edges:
        # Merge or update with temporal metadata
        return merge_with_temporal_validity(new_edge, similar_edges)
    else:
        return new_edge
```

**Temporal Validity Model**:
```python
# Every edge includes:
{
    "source": "entity_id_1",
    "target": "entity_id_2",
    "relation_type": "KNOWS",
    "created_at": "2025-01-15T10:00:00Z",
    "valid_from": "2025-01-15T10:00:00Z",  # When fact became true
    "valid_to": null,  # null = currently valid
    "fact": "Alice knows Bob through work"
}

# When conflict detected:
# - Don't delete old edge
# - Set valid_to timestamp
# - Create new edge with updated valid_from
```

**Bulk Ingestion Optimization**:
- `add_episode_bulk()` batches deduplication operations
- Significantly faster than individual `add_episode()` calls
- Recommended for offline consolidation batches

**Sources**:
- [Graphiti: Knowledge Graph Memory for an Agentic World](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
- [Building AI Knowledge Graphs with Graphiti & Neo4j](https://blog.futuresmart.ai/building-ai-knowledge-graph-using-graphiti-and-neo4j)
- [Zep Research Paper (2025)](https://arxiv.org/abs/2501.13956)

#### Memento MCP

**Architecture**: Knowledge graph memory system for LLMs with MCP (Model Context Protocol) support

**Key Features**:
- Point-in-time queries (retrieve graph state at any moment)
- Automatic timestamp tracking: `createdAt`, `updatedAt`, `validFrom`, `validTo`
- Configurable time-based decay for relation confidence
- Half-life based decay model

**Confidence Decay Formula**:
```python
import math
from datetime import datetime, timedelta

def calculate_decayed_confidence(
    original_confidence: float,
    created_at: datetime,
    half_life_days: int = 30
) -> float:
    """
    Calculate confidence with exponential decay.

    Args:
        original_confidence: Initial confidence (0-1)
        created_at: When memory was created
        half_life_days: Days for confidence to halve

    Returns:
        Decayed confidence value (0-1)
    """
    days_elapsed = (datetime.now() - created_at).days
    decay_factor = math.pow(0.5, days_elapsed / half_life_days)
    return original_confidence * decay_factor

# Example usage
confidence_after_60_days = calculate_decayed_confidence(
    original_confidence=1.0,
    created_at=datetime.now() - timedelta(days=60),
    half_life_days=30
)
# Result: 0.25 (halved twice: 1.0 → 0.5 → 0.25)
```

**Sources**:
- [Memento MCP GitHub](https://github.com/gannonh/memento-mcp)
- [Knowledge Graph Memory MCP Server](https://www.pulsemcp.com/servers/modelcontextprotocol-knowledge-graph-memory)

#### DynTKG (Dynamic Temporal Knowledge Graph)

**Published**: 2025 (Journal of King Saud University)

**Key Innovation**: Time-decay Hawkes process for adaptive event filtering

**Approach**:
- Filters historical events based on temporal salience
- Reconstructs subgraphs that preserve critical dependencies
- Reduces redundant computations while maintaining context

**Time-Decay Hawkes Process**:
```python
import numpy as np

def hawkes_intensity(events, current_time, base_rate=0.1, decay=0.5):
    """
    Calculate Hawkes process intensity for temporal event importance.

    Args:
        events: List of (timestamp, event) tuples
        current_time: Current timestamp
        base_rate: Baseline event rate
        decay: Temporal decay parameter

    Returns:
        Intensity value indicating event importance
    """
    intensity = base_rate
    for event_time, _ in events:
        if event_time < current_time:
            time_diff = current_time - event_time
            intensity += np.exp(-decay * time_diff)
    return intensity

# Example: Filter events by importance threshold
def filter_temporal_events(events, threshold=0.3):
    """Keep only temporally significant events."""
    current_time = max(t for t, _ in events)
    filtered = []

    for event_time, event in events:
        importance = hawkes_intensity(
            [(t, e) for t, e in events if t <= event_time],
            event_time
        )
        if importance >= threshold:
            filtered.append((event_time, event))

    return filtered
```

**Sources**:
- [Dynamic subgraph pruning and causal-aware knowledge distillation](https://link.springer.com/article/10.1007/s44443-025-00105-3)

### 1.3 Graph Pruning Strategies

#### Importance Scoring Approaches

**1. Degree Centrality** (Simple, fast)
```python
import networkx as nx

def calculate_node_importance(graph: nx.DiGraph) -> dict:
    """
    Calculate importance based on degree centrality.
    Higher degree = more connected = more important.
    """
    centrality = nx.degree_centrality(graph)
    return {node: score for node, score in centrality.items()}

# Usage
importance_scores = calculate_node_importance(memory_graph)
threshold = 0.05  # Keep top 95%
nodes_to_prune = [n for n, score in importance_scores.items()
                  if score < threshold]
```

**2. PageRank** (Better for directed graphs)
```python
def pagerank_importance(graph: nx.DiGraph, damping=0.85) -> dict:
    """
    Use PageRank to identify important nodes.
    Accounts for both quantity and quality of connections.
    """
    return nx.pagerank(graph, alpha=damping)

# Prune low-PageRank nodes
pagerank_scores = pagerank_importance(memory_graph)
threshold = np.percentile(list(pagerank_scores.values()), 10)
nodes_to_prune = [n for n, score in pagerank_scores.items()
                  if score < threshold]
```

**3. Composite Scoring** (Recommended)
```python
from datetime import datetime, timedelta

def composite_importance_score(
    graph: nx.DiGraph,
    node_id: str,
    access_counts: dict,
    recency_weight: float = 0.3,
    connectivity_weight: float = 0.4,
    access_weight: float = 0.3
) -> float:
    """
    Combine multiple signals for node importance.

    Args:
        graph: NetworkX graph
        node_id: Node to score
        access_counts: Dict of {node_id: access_count}
        recency_weight: Weight for temporal recency (0-1)
        connectivity_weight: Weight for graph centrality (0-1)
        access_weight: Weight for access frequency (0-1)

    Returns:
        Composite importance score (0-1)
    """
    # 1. Recency score
    node_data = graph.nodes[node_id]
    created_at = node_data.get('created_at', datetime.now())
    days_old = (datetime.now() - created_at).days
    recency_score = 1.0 / (1.0 + days_old / 30.0)  # Decay over 30 days

    # 2. Connectivity score (PageRank)
    pagerank_scores = nx.pagerank(graph)
    connectivity_score = pagerank_scores[node_id]

    # 3. Access frequency score
    max_accesses = max(access_counts.values()) if access_counts else 1
    access_score = access_counts.get(node_id, 0) / max_accesses

    # Weighted combination
    total_score = (
        recency_weight * recency_score +
        connectivity_weight * connectivity_score +
        access_weight * access_score
    )

    return total_score

# Usage
access_counts = {}  # Track in your MemoryGraph class
for node in graph.nodes():
    score = composite_importance_score(graph, node, access_counts)
    if score < 0.2:  # Prune bottom 20%
        graph.remove_node(node)
```

**Sources**:
- [Graph Database Pruning for Knowledge Representation in LLMs](https://dzone.com/articles/graph-database-pruning-for-knowledge-representation-in-llms)
- [Temporal Dual-Depth Scoring (TDDS)](https://arxiv.org/abs/2311.13613)

### 1.4 Memory Consolidation Operations

#### Four Core Operations (from AI Memory Research)

**1. Consolidation**: Moving short-term to long-term memory
```python
class MemoryConsolidator:
    def __init__(self, graph, min_access_count=3, min_age_days=7):
        self.graph = graph
        self.min_access_count = min_access_count
        self.min_age_days = min_age_days

    def consolidate_memories(self, access_log: dict):
        """
        Promote frequently accessed short-term memories.

        Args:
            access_log: {node_id: (access_count, last_accessed)}
        """
        for node_id in list(self.graph.nodes()):
            node_data = self.graph.nodes[node_id]

            # Skip if already consolidated
            if node_data.get('memory_type') == 'long_term':
                continue

            # Check consolidation criteria
            access_count, last_accessed = access_log.get(
                node_id, (0, datetime.now())
            )
            age_days = (datetime.now() - node_data['created_at']).days

            if (access_count >= self.min_access_count
                and age_days >= self.min_age_days):
                # Promote to long-term
                self.graph.nodes[node_id]['memory_type'] = 'long_term'
                self.graph.nodes[node_id]['consolidated_at'] = datetime.now()
```

**2. Indexing**: Organizing memories for efficient retrieval
```python
def create_semantic_clusters(graph, embeddings: dict, n_clusters=10):
    """
    Group similar nodes into semantic clusters.

    Args:
        graph: NetworkX graph
        embeddings: {node_id: embedding_vector}
        n_clusters: Number of clusters
    """
    from sklearn.cluster import KMeans

    node_ids = list(embeddings.keys())
    embedding_matrix = np.array([embeddings[nid] for nid in node_ids])

    # Cluster nodes
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_labels = kmeans.fit_predict(embedding_matrix)

    # Add cluster metadata
    for node_id, cluster_id in zip(node_ids, cluster_labels):
        graph.nodes[node_id]['cluster_id'] = int(cluster_id)

    return graph
```

**3. Updating**: Modifying existing memories with new information
```python
def merge_duplicate_nodes(
    graph,
    node1_id: str,
    node2_id: str,
    similarity_threshold=0.85
):
    """
    Merge two similar nodes, preserving temporal history.
    """
    node1 = graph.nodes[node1_id]
    node2 = graph.nodes[node2_id]

    # Keep the older node, merge newer into it
    if node1['created_at'] <= node2['created_at']:
        primary, secondary = node1_id, node2_id
    else:
        primary, secondary = node2_id, node1_id

    # Merge attributes
    graph.nodes[primary]['merged_from'] = graph.nodes[primary].get(
        'merged_from', []
    ) + [secondary]
    graph.nodes[primary]['updated_at'] = datetime.now()

    # Transfer edges
    for successor in graph.successors(secondary):
        if not graph.has_edge(primary, successor):
            edge_data = graph.edges[secondary, successor]
            graph.add_edge(primary, successor, **edge_data)

    for predecessor in graph.predecessors(secondary):
        if not graph.has_edge(predecessor, primary):
            edge_data = graph.edges[predecessor, secondary]
            graph.add_edge(predecessor, primary, **edge_data)

    # Remove duplicate
    graph.remove_node(secondary)

    return primary
```

**4. Forgetting**: Removing outdated or irrelevant information
```python
def prune_by_temporal_decay(
    graph,
    half_life_days=30,
    min_confidence=0.1
):
    """
    Remove nodes/edges with decayed confidence below threshold.
    """
    nodes_to_remove = []

    for node_id in graph.nodes():
        node_data = graph.nodes[node_id]
        created_at = node_data['created_at']
        original_confidence = node_data.get('confidence', 1.0)

        # Calculate decayed confidence
        days_old = (datetime.now() - created_at).days
        decay_factor = math.pow(0.5, days_old / half_life_days)
        current_confidence = original_confidence * decay_factor

        # Update or prune
        if current_confidence < min_confidence:
            nodes_to_remove.append(node_id)
        else:
            graph.nodes[node_id]['confidence'] = current_confidence

    graph.remove_nodes_from(nodes_to_remove)
    return len(nodes_to_remove)
```

**Sources**:
- [Rethinking Memory in AI: Taxonomy, Operations, Topics](https://arxiv.org/html/2505.00675v2)
- [AI Agents: Memory Systems and Graph Database Integration](https://www.falkordb.com/blog/ai-agents-memory-systems/)

### 1.5 Batch Processing Pattern for Background Consolidation

```python
import schedule
import time
from threading import Thread

class SleepConsolidationScheduler:
    """
    Background scheduler for periodic memory consolidation.
    Inspired by sleep cycles in neuroscience.
    """

    def __init__(self, memory_graph, interval_hours=24):
        self.memory_graph = memory_graph
        self.interval_hours = interval_hours
        self.is_running = False
        self.thread = None

    def consolidate_cycle(self):
        """
        Run a full consolidation cycle (analogous to sleep).
        """
        print(f"[{datetime.now()}] Starting consolidation cycle...")

        # 1. Deduplication
        duplicates_merged = self.memory_graph.deduplicate_nodes(
            similarity_threshold=0.85
        )
        print(f"  ✓ Merged {duplicates_merged} duplicate nodes")

        # 2. Temporal decay
        nodes_pruned = self.memory_graph.apply_temporal_decay(
            half_life_days=30,
            min_confidence=0.1
        )
        print(f"  ✓ Pruned {nodes_pruned} decayed nodes")

        # 3. Importance-based pruning
        low_importance_pruned = self.memory_graph.prune_by_importance(
            threshold_percentile=10  # Bottom 10%
        )
        print(f"  ✓ Pruned {low_importance_pruned} low-importance nodes")

        # 4. Cluster indexing
        self.memory_graph.create_semantic_clusters(n_clusters=10)
        print(f"  ✓ Re-indexed semantic clusters")

        # 5. Persist changes
        self.memory_graph.save()
        print(f"[{datetime.now()}] Consolidation cycle complete")

    def start(self):
        """Start background consolidation scheduler."""
        self.is_running = True

        # Schedule consolidation
        schedule.every(self.interval_hours).hours.do(self.consolidate_cycle)

        # Run in background thread
        def run_schedule():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        self.thread = Thread(target=run_schedule, daemon=True)
        self.thread.start()
        print(f"Consolidation scheduler started (every {self.interval_hours}h)")

    def stop(self):
        """Stop background scheduler."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("Consolidation scheduler stopped")

# Usage
scheduler = SleepConsolidationScheduler(
    memory_graph=my_memory_graph,
    interval_hours=24  # Daily consolidation
)
scheduler.start()

# Or run manually
scheduler.consolidate_cycle()
```

**Sources**:
- [Memory consolidation during sleep (Nature Neuroscience)](https://www.nature.com/articles/s41593-019-0467-3)
- [Sleep-dependent memory consolidation (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3278619/)

---

## 2. Local LLM Support (Ollama)

### 2.1 Overview

Ollama enables running LLMs locally with a simple API. Key advantages:
- **Privacy**: All data stays on-device
- **Cost**: No API fees after initial setup
- **Offline**: Works without internet
- **Speed**: Low latency for smaller models

### 2.2 Ollama Python SDK Usage

#### Installation
```bash
pip install ollama
```

#### Basic Usage
```python
from ollama import chat, ChatResponse

# Simple chat
response: ChatResponse = chat(
    model='llama3.2:3b',
    messages=[
        {'role': 'user', 'content': 'Why is the sky blue?'}
    ]
)
print(response.message.content)
```

#### Structured Output with Pydantic (Recommended)
```python
from pydantic import BaseModel
from ollama import chat

class ExtractedEntity(BaseModel):
    name: str
    entity_type: str  # Person, Organization, Location
    confidence: float

class EntityExtraction(BaseModel):
    entities: list[ExtractedEntity]

# Generate structured output
response = chat(
    model='llama3.2:3b',
    messages=[{
        'role': 'user',
        'content': 'Extract entities from: Alice works at Google in New York.'
    }],
    format=EntityExtraction.model_json_schema(),
    options={'temperature': 0}  # Lower temp for deterministic output
)

# Validate and parse
result = EntityExtraction.model_validate_json(response.message.content)
for entity in result.entities:
    print(f"{entity.name} ({entity.entity_type}): {entity.confidence}")
```

**Important Notes**:
- Use `format=YourModel.model_json_schema()` for Pydantic models
- Set `temperature=0` for more deterministic completions
- Include JSON instructions in the prompt for better results
- Ollama validates structure but not full JSON completeness

**Sources**:
- [Ollama Structured Outputs Documentation](https://docs.ollama.com/capabilities/structured-outputs)
- [Ollama Python SDK Examples](https://deepwiki.com/ollama/ollama-python/4.4-structured-outputs)
- [Structured Outputs with Ollama Guide](https://python.useinstructor.com/integrations/ollama/)

#### Function Calling (Tools)
```python
from ollama import chat

def get_current_weather(location: str, unit: str = "celsius") -> dict:
    """
    Get the current weather for a location.

    Args:
        location: City name
        unit: Temperature unit (celsius or fahrenheit)
    """
    # Dummy implementation
    return {"location": location, "temperature": 22, "unit": unit}

# Chat with tools
messages = [{'role': 'user', 'content': 'What is the weather in Paris?'}]

response = chat(
    model='llama3.2:3b',
    messages=messages,
    tools=[get_current_weather]  # Auto-generates schema from function
)

# Process tool calls
if response.message.tool_calls:
    for tool in response.message.tool_calls:
        if tool.function.name == 'get_current_weather':
            result = get_current_weather(**tool.function.arguments)

            # Continue conversation with result
            messages.append(response.message)
            messages.append({
                'role': 'tool',
                'content': str(result),
                'tool_name': tool.function.name
            })

    # Get final response
    final = chat(model='llama3.2:3b', messages=messages)
    print(final.message.content)
```

**Supported Models for Function Calling**:
- llama3.1, llama3.2
- mistral-nemo
- qwen2.5

**Sources**:
- [Ollama Function Calling Documentation](https://context7.com/ollama/ollama-python/llms.txt)

#### Client Configuration
```python
from ollama import Client, AsyncClient
import asyncio

# Custom client with timeout
client = Client(
    host='http://localhost:11434',
    headers={'x-api-key': 'optional-key'},
    timeout=60.0  # Longer timeout for large models
)

response = client.chat(
    model='llama3.2:3b',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

# Async client
async def async_chat():
    client = AsyncClient(host='http://localhost:11434')
    response = await client.chat(
        model='llama3.2:3b',
        messages=[{'role': 'user', 'content': 'Hello async'}]
    )
    print(response.message.content)

asyncio.run(async_chat())
```

**Sources**:
- [Configure Custom Ollama Clients](https://context7.com/ollama/ollama-python/llms.txt)

### 2.3 Making LLM Backends Swappable

#### Option 1: LiteLLM (Recommended)

**Why LiteLLM**:
- Single interface for 100+ LLM providers
- OpenAI-compatible API
- Automatic fallbacks and load balancing
- Cost tracking built-in

**Installation**:
```bash
pip install litellm
```

**Basic Swappable Pattern**:
```python
from litellm import completion
import os

# Set API keys
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

messages = [{"content": "Hello, how are you?", "role": "user"}]

# OpenAI
response = completion(
    model="gpt-4o",
    messages=messages
)

# Anthropic Claude
response = completion(
    model="claude-sonnet-4-20250514",
    messages=messages
)

# Ollama (local)
response = completion(
    model="ollama/llama3.2:3b",
    messages=messages
)

# All return same format!
print(response.choices[0].message.content)
```

**Automatic Fallbacks**:
```python
response = completion(
    model="gpt-4o",
    messages=messages,
    fallbacks=[
        "claude-sonnet-4-20250514",
        "ollama/llama3.2:3b"  # Local fallback if APIs fail
    ]
)
```

**Structured Output with LiteLLM**:
```python
from litellm import completion
from pydantic import BaseModel

class EntityExtraction(BaseModel):
    entities: list[dict]

# Works with any provider
response = completion(
    model="ollama/llama3.2:3b",  # Or gpt-4o, claude, etc.
    messages=[{"role": "user", "content": "Extract entities..."}],
    response_format=EntityExtraction  # Pydantic model
)
```

**Sources**:
- [LiteLLM Python SDK Guide](https://dev.to/yigit-konur/everything-you-need-to-know-about-litellm-python-sdk-3kfk)
- [LiteLLM Documentation](https://docs.litellm.ai/docs/)
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)

#### Option 2: Custom Abstraction Layer

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generate chat completion."""
        pass

    @abstractmethod
    def structured_output(
        self,
        messages: List[Dict[str, str]],
        schema: BaseModel,
        **kwargs
    ) -> BaseModel:
        """Generate structured output matching schema."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(api_key=api_key, model=model)

    def chat(self, messages, temperature=0.7, **kwargs):
        from langchain_core.messages import HumanMessage, SystemMessage

        lc_messages = []
        for msg in messages:
            if msg["role"] == "system":
                lc_messages.append(SystemMessage(content=msg["content"]))
            else:
                lc_messages.append(HumanMessage(content=msg["content"]))

        response = self.llm.invoke(lc_messages, temperature=temperature)
        return response.content

    def structured_output(self, messages, schema, **kwargs):
        structured_llm = self.llm.with_structured_output(
            schema,
            method="function_calling"
        )
        response = structured_llm.invoke(messages)
        return response

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434"):
        from ollama import Client
        self.client = Client(host=host)
        self.model = model

    def chat(self, messages, temperature=0.7, **kwargs):
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={'temperature': temperature}
        )
        return response.message.content

    def structured_output(self, messages, schema, **kwargs):
        response = self.client.chat(
            model=self.model,
            messages=messages,
            format=schema.model_json_schema(),
            options={'temperature': 0}
        )
        return schema.model_validate_json(response.message.content)

# Factory pattern
class LLMFactory:
    @staticmethod
    def create_provider(provider_type: str, **config) -> LLMProvider:
        if provider_type == "openai":
            return OpenAIProvider(**config)
        elif provider_type == "ollama":
            return OllamaProvider(**config)
        else:
            raise ValueError(f"Unknown provider: {provider_type}")

# Usage
provider = LLMFactory.create_provider(
    provider_type="ollama",  # or "openai"
    model="llama3.2:3b"
)

# Same interface for both
response = provider.chat([
    {"role": "user", "content": "Hello!"}
])

# Structured output
from pydantic import BaseModel

class Entity(BaseModel):
    name: str
    type: str

extraction = provider.structured_output(
    messages=[{"role": "user", "content": "Extract entities from: Alice at Google"}],
    schema=Entity
)
```

**Sources**:
- [Using OpenAI SDK with Local Ollama Models](https://safjan.com/openai-python-sdk-with-local-ollama-models-and-alternatives/)

#### Option 3: Ollama OpenAI Compatibility Mode

Ollama can emulate the OpenAI API, allowing drop-in replacement:

```python
from openai import OpenAI

# Point OpenAI client to Ollama
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama'  # Dummy key required
)

# Use OpenAI SDK with local models
response = client.chat.completions.create(
    model='llama3.2:3b',
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

**Benefits**:
- Minimal code changes
- Reuse existing OpenAI integrations
- Easy migration path

**Limitations**:
- Not all OpenAI features supported
- Requires Ollama running in OpenAI compatibility mode

**Sources**:
- [Ollama OpenAI Compatibility Guide](https://markaicode.com/ollama-openai-compatibility-setup-guide/)

### 2.4 Performance Considerations

#### Model Selection Trade-offs

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| Llama 3.2 1B | 1B params | Very Fast | Good | Simple extraction, low-resource |
| Llama 3.2 3B | 3B params | Fast | Better | **Recommended for entity extraction** |
| Llama 3.1 8B | 8B params | Moderate | High | Complex reasoning, accuracy critical |
| Qwen 2.5 7B | 7B params | Moderate | High | Multilingual, structured output |
| Mistral 7B | 7B params | Fast | High | Code generation, reasoning |

**Hardware Requirements**:
- **4-8 GB VRAM**: 1B-3B models (quantized)
- **12-16 GB VRAM**: 7B-8B models (quantized)
- **24 GB VRAM**: 13B+ models (quantized)

**Quantization**:
- Models served by Ollama are typically 4-bit quantized
- Reduces memory/VRAM by ~75% with minimal quality loss
- Example: `llama3.2:3b` vs `llama3.2:3b-q4_0`

#### Latency Comparison (Approximate)

| Operation | OpenAI GPT-4o | Ollama Llama 3.2 3B (Local) |
|-----------|---------------|------------------------------|
| Simple completion | 500-1000ms | 100-300ms |
| Structured output | 800-1500ms | 200-500ms |
| Batch (10 items) | 3000-5000ms | 1000-2000ms |

**Note**: Local models avoid network latency but depend on hardware.

**Sources**:
- [Gemma 2B vs Llama 3.2 vs Qwen 7B Performance](https://www.analyticsvidhya.com/blog/2025/01/gemma-2b-vs-llama-3-2-vs-qwen-7b/)
- [Best Local LLM Models 2025](https://blog.n8n.io/open-source-llm/)

### 2.5 Model Recommendations for Entity Extraction

Based on 2025 research comparing entity extraction performance:

#### Top Performers

**1. Gemma 2B** (Highest Overall Accuracy)
- Best overall entity extraction accuracy
- Smallest model with good performance
- Fast inference
- **Limitation**: Smaller context window

**2. Llama 3.2 3B** (Recommended)
- Second-best overall accuracy
- **Excellent for "People" entities** (highest in category)
- 128K context window
- Good balance of speed/quality
- Strong function calling support

**3. Qwen 2.5 7B** (Multilingual)
- Perfect accuracy for "People" entities
- Excellent multilingual support (29+ languages)
- Lower accuracy for "Project" and "Company" entities
- Best for non-English use cases

**For CognitiveOS**: **Llama 3.2 3B** is recommended because:
- Good entity extraction accuracy across categories
- Fast inference (local)
- Structured output support
- 128K context for conversation history
- Cost: $0.02/M tokens (or free if self-hosted)

**Sources**:
- [Gemma 2B vs Llama 3.2 vs Qwen 7B Comparison](https://www.analyticsvidhya.com/blog/2025/01/gemma-2b-vs-llama-3-2-vs-qwen-7b/)
- [Top Open-Source LLMs 2025](https://huggingface.co/blog/daya-shankar/open-source-llms)

### 2.6 Example: Swappable Extractor Implementation

```python
# src/agents/extractor_v2.py

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Import both providers
from langchain_openai import ChatOpenAI
try:
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# Existing Pydantic models from your extractor.py
class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
    properties: dict = Field(default_factory=dict)

class ExtractedRelation(BaseModel):
    source: str
    target: str
    relation_type: str
    properties: dict = Field(default_factory=dict)

class EntityExtraction(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relations: List[ExtractedRelation] = Field(default_factory=list)

class ExtractionAgent:
    """
    Unified entity extraction agent supporting multiple LLM backends.
    """

    def __init__(
        self,
        provider: str = "openai",  # "openai" or "ollama"
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        ollama_host: str = "http://localhost:11434"
    ):
        self.provider = provider.lower()

        if self.provider == "openai":
            self.model = model or "gpt-4o"
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                model=self.model,
                temperature=0
            )
            self.structured_llm = self.llm.with_structured_output(
                EntityExtraction,
                method="function_calling"
            )

        elif self.provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ImportError("ollama package not installed")

            self.model = model or "llama3.2:3b"
            self.ollama_host = ollama_host
            self.client = OllamaClient(host=ollama_host)

            # Test connection
            try:
                self.client.list()
            except Exception as e:
                raise ConnectionError(
                    f"Cannot connect to Ollama at {ollama_host}. "
                    f"Ensure Ollama is running. Error: {e}"
                )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def extract(self, text: str) -> EntityExtraction:
        """
        Extract entities and relations from text.

        Args:
            text: Input text to analyze

        Returns:
            EntityExtraction with entities and relations
        """
        prompt = self._build_prompt(text)

        if self.provider == "openai":
            return self._extract_openai(prompt)
        elif self.provider == "ollama":
            return self._extract_ollama(prompt)

    def _build_prompt(self, text: str) -> str:
        """Build extraction prompt."""
        return f"""Extract entities and relations from the following text.

Entities should include:
- People (name, age, occupation, etc.)
- Organizations (name, industry, etc.)
- Locations (city, country, etc.)
- Skills (programming languages, tools, etc.)
- Preferences (likes, dislikes, etc.)

Relations should capture connections like:
- KNOWS (person-person)
- WORKS_AT (person-organization)
- LIVES_IN (person-location)
- LIKES (person-anything)
- HAS_SKILL (person-skill)

Text: {text}

Return JSON with "entities" and "relations" arrays."""

    def _extract_openai(self, prompt: str) -> EntityExtraction:
        """Extract using OpenAI."""
        messages = [{"role": "user", "content": prompt}]
        return self.structured_llm.invoke(messages)

    def _extract_ollama(self, prompt: str) -> EntityExtraction:
        """Extract using Ollama with structured output."""
        messages = [{"role": "user", "content": prompt}]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            format=EntityExtraction.model_json_schema(),
            options={"temperature": 0}
        )

        # Parse and validate
        return EntityExtraction.model_validate_json(
            response.message.content
        )

# Usage examples
if __name__ == "__main__":
    # Test with OpenAI
    openai_agent = ExtractionAgent(provider="openai")
    result = openai_agent.extract(
        "Alice is a Python developer at Google in San Francisco. "
        "She knows Bob from college and likes machine learning."
    )
    print("OpenAI Extraction:", result)

    # Test with Ollama (local)
    ollama_agent = ExtractionAgent(
        provider="ollama",
        model="llama3.2:3b"
    )
    result = ollama_agent.extract(
        "Alice is a Python developer at Google in San Francisco. "
        "She knows Bob from college and likes machine learning."
    )
    print("Ollama Extraction:", result)
```

**Environment Configuration**:
```bash
# .env
LLM_PROVIDER=ollama  # or "openai"
LLM_MODEL=llama3.2:3b  # or "gpt-4o"
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=sk-...  # Only needed if provider=openai
```

---

## 3. Implementation Recommendations

### 3.1 Phase 3 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CognitiveOS v0.3.0                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  LLM Provider    │         │  Memory Consolidation   │  │
│  │  (Swappable)     │         │  (Background Scheduler) │  │
│  ├──────────────────┤         ├─────────────────────────┤  │
│  │ • OpenAI GPT-4o  │         │ • Deduplication         │  │
│  │ • Ollama Llama   │         │ • Temporal Decay        │  │
│  │ • LiteLLM        │         │ • Importance Pruning    │  │
│  └────────┬─────────┘         │ • Cluster Indexing      │  │
│           │                   └──────────┬──────────────┘  │
│           │                              │                 │
│           ▼                              ▼                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │          CognitiveLoop (LangGraph)                  │   │
│  │  ┌─────────┐    ┌──────────┐    ┌──────────────┐   │   │
│  │  │Retrieve │───▶│ Generate │───▶│   Extract    │   │   │
│  │  │ Context │    │ Response │    │   & Store    │   │   │
│  │  └─────────┘    └──────────┘    └──────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│           │                              │                 │
│           ▼                              ▼                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MemoryGraph (Enhanced)                 │   │
│  │  • Node deduplication (semantic similarity)         │   │
│  │  • Temporal metadata (created_at, confidence)       │   │
│  │  • Importance scoring (PageRank + recency + access) │   │
│  │  • Cluster indexing (KMeans on embeddings)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                 │
│                          ▼                                 │
│         ┌────────────────────────────────┐                 │
│         │   Storage Backend (Existing)   │                 │
│         │   • JSON (NetworkX)            │                 │
│         │   • SQLite + sqlite-vec        │                 │
│         └────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation Steps

#### Step 1: Add Ollama Support (Priority: High)

**Files to modify**:
- `src/agents/extractor.py` → Add Ollama backend
- `requirements.txt` → Add `ollama` package
- `.env.example` → Add Ollama config variables
- `CLAUDE.md` → Document new env vars

**Tasks**:
1. Create `ExtractionAgent` wrapper class with swappable backends
2. Add Ollama provider using Pydantic structured output
3. Add environment variables for provider selection
4. Test with Llama 3.2 3B model
5. Update documentation

**Estimated effort**: 4-6 hours

#### Step 2: Implement Memory Consolidation (Priority: High)

**Files to create/modify**:
- `src/memory/consolidation.py` → New module with consolidation logic
- `src/memory/graph.py` → Add deduplication and pruning methods
- `src/memory/scheduler.py` → Background consolidation scheduler

**Core features**:
1. **Deduplication**:
   - Semantic similarity-based node merging
   - Edge deduplication between same entity pairs
   - Threshold: 0.85 similarity

2. **Temporal Decay**:
   - Exponential confidence decay (half-life = 30 days)
   - Prune nodes below 0.1 confidence
   - Preserve temporal history

3. **Importance Scoring**:
   - Composite score: recency (30%) + connectivity (40%) + access (30%)
   - Prune bottom 10% periodically

4. **Cluster Indexing**:
   - K-Means clustering on embeddings
   - 10 clusters for faster retrieval
   - Update cluster metadata

**Estimated effort**: 12-16 hours

#### Step 3: Background Scheduler (Priority: Medium)

**Files to create**:
- `src/memory/scheduler.py` → Consolidation scheduler

**Features**:
1. Configurable interval (default: 24 hours)
2. Thread-based background execution
3. Manual trigger option
4. Logging of consolidation metrics

**Estimated effort**: 4-6 hours

#### Step 4: Configuration & Testing (Priority: High)

**Files to update**:
- `.env.example` → All new config options
- `CLAUDE.md` → Architecture updates
- `tests/test_consolidation.py` → New test suite

**Configuration**:
```bash
# LLM Provider
LLM_PROVIDER=ollama  # "openai" or "ollama"
LLM_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434

# Memory Consolidation
CONSOLIDATION_ENABLED=true
CONSOLIDATION_INTERVAL_HOURS=24
DEDUPLICATION_THRESHOLD=0.85
TEMPORAL_DECAY_HALF_LIFE_DAYS=30
MIN_CONFIDENCE_THRESHOLD=0.1
IMPORTANCE_PRUNE_PERCENTILE=10
```

**Estimated effort**: 6-8 hours

### 3.3 Total Estimated Effort

| Task | Effort | Priority |
|------|--------|----------|
| Ollama Support | 4-6 hours | High |
| Memory Consolidation | 12-16 hours | High |
| Background Scheduler | 4-6 hours | Medium |
| Config & Testing | 6-8 hours | High |
| **Total** | **26-36 hours** | - |

### 3.4 Optional Enhancements (Future)

1. **LiteLLM Integration** (4-6 hours)
   - Replace custom abstraction with LiteLLM
   - Automatic fallbacks (GPT-4o → Claude → Llama)
   - Cost tracking

2. **Advanced Consolidation** (8-12 hours)
   - Community detection (Louvain algorithm)
   - Hierarchical memory (episodic → semantic → consolidated)
   - Active forgetting with reinforcement

3. **Web UI Enhancements** (6-8 hours)
   - Consolidation dashboard in Streamlit
   - Real-time consolidation metrics
   - Manual consolidation trigger button

---

## 4. References

### Academic Papers

1. **Zep: A Temporal Knowledge Graph Architecture for Agent Memory**
   Rasmussen et al., 2025
   https://arxiv.org/abs/2501.13956

2. **Rethinking Memory in AI: Taxonomy, Operations, Topics, and Future Directions**
   2025
   https://arxiv.org/html/2505.00675v2

3. **Dynamic subgraph pruning and causal-aware knowledge distillation for temporal knowledge graphs**
   Journal of King Saud University, 2025
   https://link.springer.com/article/10.1007/s44443-025-00105-3

4. **Temporal Dual-Depth Scoring (TDDS) for Enhanced Dataset Pruning**
   2023
   https://arxiv.org/abs/2311.13613

5. **Mechanisms of systems memory consolidation during sleep**
   Nature Neuroscience, 2019
   https://www.nature.com/articles/s41593-019-0467-3

6. **Sleep—A brain-state serving systems memory consolidation**
   ScienceDirect, 2023
   https://www.sciencedirect.com/science/article/pii/S0896627323002015

### Industry Frameworks

7. **Graphiti - Knowledge Graph Memory for AI Agents**
   Neo4j Blog
   https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/

8. **Building AI Knowledge Graphs with Graphiti & Neo4j**
   https://blog.futuresmart.ai/building-ai-knowledge-graph-using-graphiti-and-neo4j

9. **Graphiti GitHub Repository**
   https://github.com/getzep/graphiti

10. **Memento MCP - Knowledge Graph Memory System**
    https://github.com/gannonh/memento-mcp

11. **AI Agents: Memory Systems and Graph Database Integration**
    FalkorDB Blog
    https://www.falkordb.com/blog/ai-agents-memory-systems/

### Ollama & Local LLMs

12. **Ollama Structured Outputs Documentation**
    https://docs.ollama.com/capabilities/structured-outputs

13. **Ollama Python SDK - Structured Outputs Guide**
    https://python.useinstructor.com/integrations/ollama/

14. **Ollama Python Library Documentation**
    https://deepwiki.com/ollama/ollama-python/

15. **Gemma 2B vs Llama 3.2 vs Qwen 7B Entity Extraction Comparison**
    Analytics Vidhya, 2025
    https://www.analyticsvidhya.com/blog/2025/01/gemma-2b-vs-llama-3-2-vs-qwen-7b/

16. **10 Best Open-Source LLM Models (2025 Updated)**
    Hugging Face Blog
    https://huggingface.co/blog/daya-shankar/open-source-llms

17. **The 11 Best Open-Source LLMs for 2025**
    n8n Blog
    https://blog.n8n.io/open-source-llm/

### LLM Abstraction & Swappable Backends

18. **LiteLLM Python SDK Guide**
    DEV Community
    https://dev.to/yigit-konur/everything-you-need-to-know-about-litellm-python-sdk-3kfk

19. **LiteLLM Documentation**
    https://docs.litellm.ai/docs/

20. **LiteLLM GitHub Repository**
    https://github.com/BerriAI/litellm

21. **Using OpenAI Python SDK with Local Ollama Models**
    https://safjan.com/openai-python-sdk-with-local-ollama-models-and-alternatives/

22. **Ollama OpenAI Compatibility Setup Guide**
    https://markaicode.com/ollama-openai-compatibility-setup-guide/

23. **A Gentle Introduction to LiteLLM**
    Medium, 2025
    https://medium.com/mitb-for-all/a-gentle-introduction-to-litellm-649d48a0c2c7

### Graph Pruning & Consolidation

24. **Graph Database Pruning for Knowledge Representation in LLMs**
    DZone
    https://dzone.com/articles/graph-database-pruning-for-knowledge-representation-in-llms

25. **Task-driven cleaning and pruning of noisy knowledge graphs**
    ScienceDirect
    https://www.sciencedirect.com/science/article/abs/pii/S002002552300991X

26. **Beyond the Bubble: Context-Aware Memory Systems in 2025**
    Tribe AI
    https://www.tribe.ai/applied-ai/beyond-the-bubble-how-context-aware-memory-systems-are-changing-the-game-in-2025

### Memory Systems & Architecture

27. **Exploring Memory Options for Agent-Based Systems**
    MarkTechPost
    https://www.marktechpost.com/2024/11/26/exploring-memory-options-for-agent-based-systems-a-comprehensive-overview/

28. **From Context to Consciousness: Long-Term Memory in AI Agents**
    Medium, 2025
    https://prajnaaiwisdom.medium.com/from-context-to-consciousness-why-long-term-memory-will-define-the-next-generation-of-ai-agents-4cde635080fc

---

## Appendix: Quick Start Commands

### Install Ollama (if not already installed)

**Linux/macOS**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows**:
Download installer from https://ollama.com/download

### Pull Recommended Model

```bash
ollama pull llama3.2:3b
```

### Test Ollama Python SDK

```bash
pip install ollama

python -c "
from ollama import chat
response = chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': 'Hello!'}])
print(response.message.content)
"
```

### Install LiteLLM (Optional)

```bash
pip install litellm

python -c "
from litellm import completion
response = completion(model='ollama/llama3.2:3b', messages=[{'role': 'user', 'content': 'Test'}])
print(response.choices[0].message.content)
"
```

---

**End of Research Document**
