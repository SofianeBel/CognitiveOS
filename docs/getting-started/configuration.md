# Configuration

CognitiveOS is configured through environment variables in the `.env` file.

## Environment File

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings.

## Configuration Reference

### Required

| Variable | Type | Description |
|----------|------|-------------|
| `OPENAI_API_KEY` | string | OpenAI API key (required if using OpenAI provider) |

### LLM Provider

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_PROVIDER` | string | `openai` | LLM provider: `openai` or `ollama` |
| `OLLAMA_BASE_URL` | string | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | string | `llama3.2` | Ollama model name |

### Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `STORAGE_BACKEND` | string | `json` | Storage backend: `json` or `sqlite` |
| `MEMORY_FILE` | string | `data/memory.json` | Path for JSON storage |
| `DATABASE_PATH` | string | `data/memory.db` | Path for SQLite database |

### Retrieval Tuning

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RETRIEVAL_TOP_K` | int | `10` | Number of context items to retrieve |
| `SIMILARITY_THRESHOLD` | float | `0.7` | Minimum cosine similarity (0.0-1.0) |
| `DUPLICATE_THRESHOLD` | float | `0.85` | Threshold for duplicate detection |

### Consolidation (Phase 3)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DUPLICATE_MERGE_THRESHOLD` | float | `0.9` | Similarity for duplicate merging |
| `PRUNE_INACTIVE_DAYS` | int | `30` | Days before pruning inactive nodes |
| `PRUNE_IMPORTANCE_THRESHOLD` | float | `0.3` | Max importance score to prune |

### Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

## Example Configurations

### Minimal (OpenAI + JSON)

```ini
OPENAI_API_KEY=sk-your-api-key-here
```

### Production (OpenAI + SQLite)

```ini
OPENAI_API_KEY=sk-your-api-key-here
STORAGE_BACKEND=sqlite
DATABASE_PATH=data/memory.db
RETRIEVAL_TOP_K=15
SIMILARITY_THRESHOLD=0.75
LOG_LEVEL=WARNING
```

### Local LLM (Ollama)

```ini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
STORAGE_BACKEND=sqlite
DATABASE_PATH=data/memory.db
```

### Development

```ini
OPENAI_API_KEY=sk-your-api-key-here
STORAGE_BACKEND=json
MEMORY_FILE=data/dev_memory.json
LOG_LEVEL=DEBUG
RETRIEVAL_TOP_K=5
```

## Storage Backend Comparison

| Feature | JSON | SQLite |
|---------|------|--------|
| Setup complexity | None | Requires sqlite-vec |
| Performance (small graphs) | Fast | Fast |
| Performance (large graphs) | Slow | Fast |
| Vector search | In-memory | Native (sqlite-vec) |
| ACID transactions | No | Yes |
| File portability | Yes (single JSON) | Yes (single .db) |
| Human-readable | Yes | No |
| Soft delete support | No | Yes |
| Audit logging | No | Yes |

**Recommendation:**

- **Development/Testing**: Use JSON for simplicity
- **Production**: Use SQLite for performance and features

## Retrieval Tuning

### `RETRIEVAL_TOP_K`

Number of similar entities to retrieve for context injection.

- **Lower (5-10)**: Faster, more focused context
- **Higher (15-20)**: More comprehensive, may include noise

### `SIMILARITY_THRESHOLD`

Minimum cosine similarity score for retrieval.

- **Lower (0.5-0.6)**: More results, potentially less relevant
- **Higher (0.8-0.9)**: Fewer results, higher relevance

### `DUPLICATE_THRESHOLD`

Threshold for detecting duplicate entities during extraction.

- **Lower (0.7-0.8)**: More aggressive deduplication
- **Higher (0.9-0.95)**: Only near-exact matches

## Ollama Model Selection

Tested models with CognitiveOS:

| Model | Size | RAM Required | Quality | Speed |
|-------|------|--------------|---------|-------|
| `llama3.2` | 3B | 4GB | Good | Fast |
| `llama3.2:7b` | 7B | 8GB | Better | Medium |
| `mistral` | 7B | 8GB | Good | Medium |
| `codellama` | 7B | 8GB | Good (code) | Medium |

For entity extraction quality, we recommend at least a 7B parameter model.

## Troubleshooting

### Configuration Not Loading

1. Ensure `.env` is in the project root directory
2. Check file permissions
3. Verify no syntax errors (no quotes around values unless needed)

### Ollama Connection Failed

```
Error: Connection refused to http://localhost:11434
```

1. Ensure Ollama is running: `ollama serve`
2. Check the URL matches `OLLAMA_BASE_URL`
3. Verify the model is downloaded: `ollama list`

### SQLite Vector Search Not Working

If sqlite-vec is not installed, set:

```ini
STORAGE_BACKEND=json
```

Or install sqlite-vec (see [Installation](installation.md)).

## Next Steps

- [CLI Usage](../user-guide/cli-usage.md) - Console commands
- [Local LLM Setup](../user-guide/local-llm.md) - Detailed Ollama guide
- [Migration](../user-guide/migration.md) - Move from JSON to SQLite
