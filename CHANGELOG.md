# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-12-08

### Added
- Memory consolidation engine (`python -m src.consolidation.run`)
  - Duplicate detection and merging (configurable similarity threshold)
  - Contradiction detection for conflicting relations (LIKES/DISLIKES, etc.)
  - Inactive memory pruning (configurable days and importance thresholds)
  - Dry-run mode for previewing changes
- Local LLM support via Ollama
  - LLM Factory pattern for swappable providers (`src/agents/llm_factory.py`)
  - Support for OpenAI GPT-4o and Ollama (Llama 3.2)
  - Provider switching via `LLM_PROVIDER` environment variable
- New CLI commands: `consolidate`, `provider`
- Consolidation UI in Streamlit app with preview and apply workflow
- New data models: `MergeResult`, `Contradiction`, `ConsolidationResult`

### Changed
- Configuration now supports optional `OPENAI_API_KEY` (required only for OpenAI provider)
- ExtractionAgent and CognitiveLoop now use LLMFactory for provider abstraction
- Updated requirements.txt with langchain-ollama dependency

### Configuration
New environment variables:
- `LLM_PROVIDER`: "openai" or "ollama" (default: "openai")
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Ollama model name (default: llama3.2)
- `CONSOLIDATION_ENABLED`: Enable consolidation (default: true)
- `DUPLICATE_MERGE_THRESHOLD`: Similarity for duplicate detection (default: 0.9)
- `PRUNE_INACTIVE_DAYS`: Days before pruning (default: 30)
- `PRUNE_IMPORTANCE_THRESHOLD`: Max importance to prune (default: 0.3)

## [0.2.0] - 2025-12-08

### Added
- SQLite storage backend with sqlite-vec for vector similarity search
- Streamlit web application with chat interface
- PyVis interactive graph visualization with entity type colors
- JSON to SQLite migration tool (`python -m src.memory.migrate`)
- Storage backend configuration via `STORAGE_BACKEND` env var
- Database path configuration via `DATABASE_PATH` env var

### Changed
- MemoryGraph now supports both JSON and SQLite backends
- Updated requirements.txt with Phase 2 dependencies (sqlite-vec, streamlit, pyvis)
- Configuration extended with storage_backend and database_path settings

## [0.1.0] - 2025-12-08

### Added
- Initial release with Phase 1 features
- LangGraph-based conversation loop with memory
- Entity extraction using GPT-4o structured output
- NetworkX knowledge graph with JSON persistence
- Sentence-transformers embeddings (all-MiniLM-L6-v2)
- Semantic similarity search for context retrieval
- Duplicate detection via embedding similarity
- Rich CLI interface with stats, help, clear, quit commands
- Pydantic data models for Node, Edge, ExtractionResult
- Unit tests for memory module

### Entity Types
- Person, Concept, Preference, Skill, Location, Event, Organization

### Relation Types
- KNOWS, LIKES, DISLIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED, CREATED, MEMBER_OF, HAS_PROPERTY, RELATED_TO

[Unreleased]: https://github.com/yourusername/CognitiveOS/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/yourusername/CognitiveOS/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/CognitiveOS/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/CognitiveOS/releases/tag/v0.1.0
