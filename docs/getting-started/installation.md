# Installation

This guide will help you set up CognitiveOS on your system.

## Prerequisites

- **Python 3.10+** (tested on 3.10, 3.11, 3.12)
- **Git** (for cloning the repository)
- **OpenAI API key** or **Ollama** for local LLM

## Quick Install

=== "Windows"

    ```powershell
    # Clone repository
    git clone https://github.com/sifly/CognitiveOS.git
    cd CognitiveOS

    # Create virtual environment
    python -m venv venv
    venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt
    ```

    !!! warning "sqlite-vec on Windows"

        If you encounter build errors for `sqlite-vec`, you have two options:

        **Option 1: Install Visual Studio Build Tools**

        1. Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
        2. Install "Desktop development with C++"
        3. Retry `pip install -r requirements.txt`

        **Option 2: Use JSON storage (skip sqlite-vec)**

        Edit `requirements.txt` to comment out `sqlite-vec`, then:
        ```powershell
        pip install -r requirements.txt
        ```
        CognitiveOS will automatically use JSON storage.

=== "macOS"

    ```bash
    # Clone repository
    git clone https://github.com/sifly/CognitiveOS.git
    cd CognitiveOS

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    ```

=== "Linux"

    ```bash
    # Clone repository
    git clone https://github.com/sifly/CognitiveOS.git
    cd CognitiveOS

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    ```

    !!! note "Ubuntu/Debian"
        You may need to install Python venv first:
        ```bash
        sudo apt install python3-venv python3-dev
        ```

## Environment Setup

1. **Copy the example environment file:**

    ```bash
    cp .env.example .env
    ```

2. **Edit `.env` with your configuration:**

    ```ini
    # Required for OpenAI provider
    OPENAI_API_KEY=sk-your-api-key-here

    # Storage backend (json or sqlite)
    STORAGE_BACKEND=json

    # Optional: Ollama for local LLM
    # LLM_PROVIDER=ollama
    # OLLAMA_BASE_URL=http://localhost:11434
    # OLLAMA_MODEL=llama3.2
    ```

## Verify Installation

### Run Tests

```bash
pytest tests/ -v
```

Expected output:
```
tests/test_memory.py::TestMemoryGraph::test_add_node PASSED
tests/test_memory.py::TestMemoryGraph::test_add_edge PASSED
tests/test_soft_delete.py::TestSoftDelete::test_soft_delete_preserves_node PASSED
...
========================= 20 passed in 5.23s =========================
```

### Test Console Interface

```bash
python main.py
```

You should see:
```
🧠 CognitiveOS Console
Type 'quit' to exit, 'stats' for memory statistics

You:
```

Type `quit` to exit.

## Dependencies

### Core Libraries

| Library | Purpose |
|---------|---------|
| langgraph | Conversation loop orchestration |
| langchain-openai | GPT-4o integration |
| networkx | In-memory graph structure |
| sentence-transformers | Embedding model (all-MiniLM-L6-v2) |
| pydantic | Data validation and models |

### Storage & UI

| Library | Purpose |
|---------|---------|
| sqlite-vec | Vector similarity in SQLite |
| streamlit | Web UI framework |
| pyvis | Interactive graph visualization |

### Optional (Phase 3)

| Library | Purpose |
|---------|---------|
| langchain-ollama | Local LLM integration |

## Troubleshooting Installation

### `ModuleNotFoundError: No module named 'xxx'`

Make sure your virtual environment is activated:

=== "Windows"
    ```powershell
    venv\Scripts\activate
    ```

=== "macOS/Linux"
    ```bash
    source venv/bin/activate
    ```

### `sqlite3.OperationalError: no such module: vec0`

sqlite-vec is not installed correctly. Either:

1. Install Visual Studio Build Tools (Windows)
2. Use JSON storage by setting `STORAGE_BACKEND=json` in `.env`

### `OPENAI_API_KEY not found`

Make sure your `.env` file exists and contains the API key:
```bash
cat .env | grep OPENAI
```

### Embedding model download slow

The first run downloads the `all-MiniLM-L6-v2` model (~90MB). This is normal and only happens once.

## Next Steps

- [Quick Start](quickstart.md) - Your first conversation with memory
- [Configuration](configuration.md) - Customize all settings
- [Local LLM Setup](../user-guide/local-llm.md) - Use Ollama for privacy
