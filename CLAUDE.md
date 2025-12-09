# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CognitiveOS is a local-first memory system for LLMs. It extracts entities and relations from conversations, stores them in a knowledge graph, and retrieves relevant context for personalized responses.

## Commands

### Development

```bash
# Console interface
python main.py

# Web interface (Streamlit)
streamlit run app.py

# Run tests
pytest tests/ -v

# Run single test
pytest tests/test_memory.py::TestMemoryGraph::test_add_node -v

# Migration (JSON to SQLite)
python -m src.memory.migrate --json data/memory.json --db data/memory.db
```

### Environment Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Environment Variables

```bash
# Required (for OpenAI provider)
OPENAI_API_KEY=sk-...

# LLM Provider (Phase 3)
LLM_PROVIDER=openai           # "openai" or "ollama"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Storage (optional)
STORAGE_BACKEND=json          # "json" or "sqlite"
MEMORY_FILE=data/memory.json  # JSON storage path
DATABASE_PATH=data/memory.db  # SQLite storage path

# Retrieval tuning (optional)
RETRIEVAL_TOP_K=10            # Number of context items
SIMILARITY_THRESHOLD=0.4      # Minimum similarity for retrieval (default: 0.4)
DUPLICATE_THRESHOLD=0.85      # Similarity threshold for deduplication

# Debug mode
DEBUG_MEMORY=false            # Set to "true" for verbose memory retrieval output

# Consolidation (Phase 3)
DUPLICATE_MERGE_THRESHOLD=0.9    # Similarity for duplicate detection
PRUNE_INACTIVE_DAYS=30           # Days before pruning
PRUNE_IMPORTANCE_THRESHOLD=0.3   # Max importance to prune

# Logging
LOG_LEVEL=INFO
```

## Project Tracker

project_tracker: github

## Architecture

### Core Flow (LangGraph)

```
User Message → Context Retrieval → LLM Response → Entity Extraction → Memory Storage
                     ↑                                                      ↓
                     └──────────────────────────────────────────────────────┘
```

The flow is implemented in `src/graph_loop.py` as a `CognitiveLoop` class with three nodes:
1. `retrieve_context` - Semantic search in memory graph (searches both nodes AND edges)
2. `generate_response` - GPT-4o with injected context (explicit instructions to use memories)
3. `store_memory` - Extract and persist new facts

### Storage Backends

Configured via `STORAGE_BACKEND` env var:

- **json** (default): NetworkX graph persisted to `data/memory.json`
- **sqlite**: SQLite with sqlite-vec for vector similarity, stored in `data/memory.db`

Both backends are abstracted in `src/memory/graph.py` (MemoryGraph class).

### Entity Extraction

`src/agents/extractor.py` uses GPT-4o with structured output (Pydantic models):
- `ExtractedEntity` - Person, Concept, Preference, Skill, Location, Event, Organization
- `ExtractedRelation` - HAS_NAME, IS_CALLED, KNOWS, LIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED, etc.

The prompt uses double braces `{{}}` to escape JSON examples from LangChain template parsing.

### Key Classes

- `MemoryGraph` (`src/memory/graph.py`) - Main memory interface, supports both JSON and SQLite
- `SQLiteMemoryStore` (`src/memory/database.py`) - SQLite + sqlite-vec implementation
- `CognitiveLoop` (`src/graph_loop.py`) - LangGraph orchestration
- `ExtractionAgent` (`src/agents/extractor.py`) - Entity extraction with structured output
- `EmbeddingService` (`src/memory/embeddings.py`) - Singleton for sentence-transformers
- `LLMFactory` (`src/agents/llm_factory.py`) - Provider abstraction for OpenAI/Ollama (Phase 3)
- `ConsolidationEngine` (`src/consolidation/engine.py`) - Memory optimization (Phase 3)

## Git & Versioning Conventions

### Commit Messages

Use conventional commits format:
```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
refactor: Code refactoring
test: Adding tests
```

Always include the Claude Code signature:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Branching Strategy

- `master` - Main branch, stable releases
- Feature branches for new development

### Versioning

Follow Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH (e.g., 1.0.0)
- Update CHANGELOG.md for all significant changes
- Create git tags for releases: `git tag v1.0.0`

### Releases

Before creating a release:
1. Update CHANGELOG.md with all changes since last release
2. Update version in relevant files if applicable
3. Commit: `git commit -m "chore: Release vX.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push origin master --tags`

## Known Issues & Patterns

### NetworkX add_edge

When adding edges to NetworkX, avoid duplicate kwargs. The `model_dump()` includes `id`, `source`, `target`, so remove them before spreading:
```python
edge_data = edge.model_dump()
edge_data.pop('source', None)
edge_data.pop('target', None)
self.graph.add_edge(edge.source, edge.target, **edge_data)
```

### OpenAI Structured Output

Use `method="function_calling"` for more flexible schema handling:
```python
.with_structured_output(EntityExtraction, method="function_calling")
```

### Prompt Template Escaping

JSON examples in LangChain prompts must escape braces with `{{` and `}}`:
```python
PROMPT = """
Example: {{"name": "Alice"}}
"""
```

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src

# Skip slow tests (embedding model loading)
pytest tests/ -v -m "not slow"
```

### Test Structure

Tests require `OPENAI_API_KEY` env var (can be a dummy value for unit tests).
Use `temp_memory_file` fixture for isolated file-based tests.

## Dependencies

### Core Libraries

| Library | Purpose |
|---------|---------|
| langgraph | Conversation loop orchestration |
| langchain-openai | GPT-4o integration |
| networkx | In-memory graph structure |
| sentence-transformers | Embedding model (all-MiniLM-L6-v2) |
| pydantic | Data validation and models |

### Phase 2 Libraries

| Library | Purpose |
|---------|---------|
| sqlite-vec | Vector similarity in SQLite |
| streamlit | Web UI framework |
| pyvis | Interactive graph visualization |

### Phase 3 Libraries

| Library | Purpose |
|---------|---------|
| langchain-ollama | Ollama LLM integration |

### Windows Notes

- sqlite-vec may require manual installation on Windows
- Use `venv\Scripts\activate` (not `source venv/bin/activate`)

## Project Phases

- **Phase 1** (Complete): Console prototype with NetworkX + JSON
- **Phase 2** (Complete): SQLite + sqlite-vec persistence, Streamlit UI with PyVis
- **Phase 3** (Complete): Memory consolidation, Local LLM support (Ollama)
- **Phase 4** (Planned): Background scheduled consolidation, Multi-user support

## Troubleshooting

### Memory not being used

If the AI doesn't seem to use stored memories:

1. **Check threshold**: Default is 0.4. The embedding model (all-MiniLM-L6-v2) produces scores of 0.3-0.55 for relevant content.
2. **Enable debug mode**: `DEBUG_MEMORY=true python main.py` to see what's being retrieved
3. **Check logs**: Look for "Retrieval:" or "No results above threshold" messages
4. **Verify data exists**: Use `stats` command in console to see node/edge counts

### Typical similarity scores

For the all-MiniLM-L6-v2 model:
- **0.5-0.6**: Very similar (near duplicates)
- **0.4-0.5**: Semantically related
- **0.3-0.4**: Loosely related
- **< 0.3**: Likely irrelevant

### Name not being remembered

If the AI doesn't remember your name when you say "je m'appelle X":

1. **Run migration**: `python -m scripts.migrate_names` to link existing name nodes
2. **Enrich descriptions**: `python -m scripts.enrich_name_nodes` to improve embeddings
3. **Check .env**: Ensure `SIMILARITY_THRESHOLD=0.4` (not 0.7)

The system now uses `HAS_NAME` relations for personal names, which requires:
- The extraction prompt recognizes "je m'appelle" and "my name is" patterns
- Enriched descriptions include multilingual keywords for better matching

## Current Version

v0.3.2 - See CHANGELOG.md for details
