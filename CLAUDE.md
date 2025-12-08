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

Required environment variable: `OPENAI_API_KEY`

## Architecture

### Core Flow (LangGraph)

```
User Message → Context Retrieval → LLM Response → Entity Extraction → Memory Storage
                     ↑                                                      ↓
                     └──────────────────────────────────────────────────────┘
```

The flow is implemented in `src/graph_loop.py` as a `CognitiveLoop` class with three nodes:
1. `retrieve_context` - Semantic search in memory graph
2. `generate_response` - GPT-4o with injected context
3. `store_memory` - Extract and persist new facts

### Storage Backends

Configured via `STORAGE_BACKEND` env var:

- **json** (default): NetworkX graph persisted to `data/memory.json`
- **sqlite**: SQLite with sqlite-vec for vector similarity, stored in `data/memory.db`

Both backends are abstracted in `src/memory/graph.py` (MemoryGraph class).

### Entity Extraction

`src/agents/extractor.py` uses GPT-4o with structured output (Pydantic models):
- `ExtractedEntity` - Person, Concept, Preference, Skill, Location, Event, Organization
- `ExtractedRelation` - KNOWS, LIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED, etc.

The prompt uses double braces `{{}}` to escape JSON examples from LangChain template parsing.

### Key Classes

- `MemoryGraph` (`src/memory/graph.py`) - Main memory interface, supports both JSON and SQLite
- `SQLiteMemoryStore` (`src/memory/database.py`) - SQLite + sqlite-vec implementation
- `CognitiveLoop` (`src/graph_loop.py`) - LangGraph orchestration
- `ExtractionAgent` (`src/agents/extractor.py`) - Entity extraction with structured output
- `EmbeddingService` (`src/memory/embeddings.py`) - Singleton for sentence-transformers

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

## Project Phases

- **Phase 1** (Complete): Console prototype with NetworkX + JSON
- **Phase 2** (Complete): SQLite + sqlite-vec persistence, Streamlit UI with PyVis
- **Phase 3** (Planned): Memory consolidation, Local LLM support (Ollama)
