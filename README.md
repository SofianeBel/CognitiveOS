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

## Architecture

```
User Message → Context Retrieval → LLM Response → Entity Extraction → Memory Storage
                     ↑                                                      ↓
                     └──────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Orchestration**: LangGraph
- **LLM**: OpenAI GPT-4o
- **Storage**: NetworkX + JSON (Phase 1), SQLite + sqlite-vec (Phase 2)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **CLI**: Rich
- **Web UI**: Streamlit + PyVis (Phase 2)

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

### Commands (Console)

| Command | Description |
|---------|-------------|
| `stats` | Show memory statistics |
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
# Required
OPENAI_API_KEY=sk-...

# Storage backend: "json" (Phase 1) or "sqlite" (Phase 2)
STORAGE_BACKEND=json

# Optional
DATABASE_PATH=data/memory.db
MEMORY_FILE=data/memory.json
```

### Migration from JSON to SQLite

```bash
python -m src.memory.migrate --json data/memory.json --db data/memory.db
```

## Roadmap

- [x] **Phase 1**: Console prototype with NetworkX
- [x] **Phase 2**: SQLite + sqlite-vec persistence
- [x] **Phase 2**: Streamlit UI with PyVis visualization
- [ ] **Phase 3**: Memory consolidation ("sleep" process)
- [ ] **Phase 3**: Local LLM support (Ollama + Llama)

## Requirements

- Python 3.10+
- OpenAI API key (Phase 1)
- ~8GB RAM minimum

## License

MIT

## Contributing

Contributions welcome! Please read the existing code and follow the patterns established.