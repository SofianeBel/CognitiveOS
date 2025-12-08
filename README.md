# CognitiveOS

**Local-First Memory System for LLMs**

CognitiveOS gives your AI assistant infinite memory. It extracts facts from conversations, stores them in a knowledge graph, and uses them to personalize future interactions.

## Features

- **Infinite Memory**: Remember everything across conversations
- **Knowledge Graph**: Entities and relationships stored in a graph structure
- **Semantic Search**: Find relevant memories using embeddings
- **Duplicate Detection**: Prevents graph fragmentation
- **Local-First**: All data stays on your machine
- **Multiple Interfaces**: Console CLI and Streamlit Web UI
- **Persistent Storage**: JSON (Phase 1) or SQLite with sqlite-vec (Phase 2)
- **Interactive Visualization**: PyVis graph with zoom, pan, and click
- **Memory Consolidation**: Merge duplicates, detect contradictions, prune stale memories (Phase 3)
- **Local LLM Support**: Offline operation with Ollama + Llama 3.2 (Phase 3)

## Architecture

```
User Message → Context Retrieval → LLM Response → Entity Extraction → Memory Storage
                     ↑                                                      ↓
                     └──────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Orchestration**: LangGraph
- **LLM**: OpenAI GPT-4o or Ollama (Llama 3.2) - configurable
- **Storage**: NetworkX + JSON (Phase 1), SQLite + sqlite-vec (Phase 2)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **CLI**: Rich
- **Web UI**: Streamlit + PyVis (Phase 2)
- **Consolidation**: Memory optimization engine (Phase 3)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/CognitiveOS.git
cd CognitiveOS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### Console Interface (Phase 1)

```bash
python main.py
```

### Web Interface (Phase 2)

```bash
streamlit run app.py
```

### Memory Consolidation (Phase 3)

```bash
# Preview consolidation changes
python -m src.consolidation.run --dry-run

# Run consolidation with custom thresholds
python -m src.consolidation.run --duplicate-threshold 0.85 --prune-days 60

# Show candidates without applying
python -m src.consolidation.run --show-candidates
```

### Commands (Console)

| Command | Description |
|---------|-------------|
| `stats` | Show memory statistics |
| `consolidate` | Run memory consolidation |
| `provider` | Show current LLM provider info |
| `help`  | Show available commands |
| `clear` | Clear the screen |
| `quit`  | Exit the program |

### Example Session

```
You: Hi! My name is Sifly and I'm a software developer.
Assistant: Nice to meet you, Sifly! What kind of development do you focus on?

You: I love Python and machine learning.
Assistant: That's great! Python is excellent for ML work. Are you working on any projects?

You: What do you know about me?
Assistant: You're Sifly, a software developer who loves Python and machine learning!
```

## Project Structure

```
CognitiveOS/
├── src/
│   ├── config.py           # Configuration management
│   ├── graph_loop.py       # LangGraph orchestration
│   ├── memory/
│   │   ├── models.py       # Pydantic data models
│   │   ├── embeddings.py   # Sentence-transformers service
│   │   ├── graph.py        # NetworkX memory graph
│   │   ├── database.py     # SQLite storage (Phase 2)
│   │   └── migrate.py      # JSON→SQLite migration (Phase 2)
│   ├── agents/
│   │   └── extractor.py    # Entity extraction agent
│   └── ui/
│       └── graph_viz.py    # PyVis visualization (Phase 2)
├── data/
│   ├── memory.json         # JSON storage (Phase 1)
│   └── memory.db           # SQLite storage (Phase 2)
├── tests/
│   └── test_memory.py      # Unit tests
├── plans/                  # Implementation plans
├── main.py                 # CLI entry point
├── app.py                  # Streamlit web app (Phase 2)
├── requirements.txt
└── .env.example
```

## Data Model

### Nodes (Entities)

```json
{
  "id": "uuid",
  "label": "Person|Concept|Preference|Skill|Location|Event|Organization",
  "name": "Alice",
  "description": "User's friend from college",
  "embedding": [0.12, -0.98, ...],
  "metadata": {
    "created_at": "2025-12-08T10:30:00Z",
    "access_count": 5,
    "importance_score": 0.8
  }
}
```

### Edges (Relations)

```json
{
  "source": "user_id",
  "target": "alice_id",
  "relation": "KNOWS|LIKES|WORKS_AT|LIVES_IN|...",
  "description": "Best friends since 2018"
}
```

## Configuration

Set these environment variables in your `.env` file:

```bash
# Required (for OpenAI provider)
OPENAI_API_KEY=sk-...

# LLM Provider: "openai" or "ollama" (Phase 3)
LLM_PROVIDER=openai

# Ollama Configuration (when LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Storage backend: "json" (Phase 1) or "sqlite" (Phase 2)
STORAGE_BACKEND=json

# Optional
DATABASE_PATH=data/memory.db
MEMORY_FILE=data/memory.json

# Consolidation Settings (Phase 3)
DUPLICATE_MERGE_THRESHOLD=0.9
PRUNE_INACTIVE_DAYS=30
PRUNE_IMPORTANCE_THRESHOLD=0.3
```

### Ollama Setup (for local LLM)

```bash
# Install Ollama
# macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh
# Windows: Download from https://ollama.com/download

# Download Llama 3.2
ollama pull llama3.2

# Set provider in .env
LLM_PROVIDER=ollama
```

### Migration from JSON to SQLite

```bash
python -m src.memory.migrate --json data/memory.json --db data/memory.db
```

## Roadmap

- [x] **Phase 1**: Console prototype with NetworkX
- [x] **Phase 2**: SQLite + sqlite-vec persistence
- [x] **Phase 2**: Streamlit UI with PyVis visualization
- [x] **Phase 3**: Memory consolidation ("sleep" process)
- [x] **Phase 3**: Local LLM support (Ollama + Llama)
- [ ] **Phase 4**: Background scheduled consolidation
- [ ] **Phase 4**: Multi-user support

## Requirements

- Python 3.10+
- OpenAI API key (for OpenAI provider) OR Ollama (for local LLM)
- ~8GB RAM minimum

## License

MIT

## Contributing

Contributions welcome! Please read the existing code and follow the patterns established.