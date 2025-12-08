# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/yourusername/CognitiveOS/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yourusername/CognitiveOS/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/yourusername/CognitiveOS/releases/tag/v0.1.0
