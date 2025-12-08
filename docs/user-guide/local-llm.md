# Local LLM Setup

Use Ollama to run CognitiveOS with a local LLM for complete privacy.

## Prerequisites

- Ollama installed ([ollama.ai](https://ollama.ai))
- Sufficient RAM for your chosen model

## Installation

### Install Ollama

=== "macOS"
    ```bash
    brew install ollama
    ```

=== "Linux"
    ```bash
    curl -fsSL https://ollama.ai/install.sh | sh
    ```

=== "Windows"
    Download from [ollama.ai/download](https://ollama.ai/download/windows)

### Download a Model

```bash
# Recommended: Llama 3.2 (3B)
ollama pull llama3.2

# Or larger model for better quality
ollama pull llama3.2:7b
```

### Start Ollama Server

```bash
ollama serve
```

## Configuration

Update your `.env` file:

```ini
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Model Selection

| Model | Size | RAM | Quality | Speed |
|-------|------|-----|---------|-------|
| `llama3.2` | 3B | 4GB | Good | Fast |
| `llama3.2:7b` | 7B | 8GB | Better | Medium |
| `llama3.2:13b` | 13B | 16GB | Best | Slow |
| `mistral` | 7B | 8GB | Good | Medium |
| `codellama` | 7B | 8GB | Good (code) | Medium |

**Recommendation:** Start with `llama3.2` (3B), upgrade if extraction quality is insufficient.

## Verification

```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# List available models
ollama list

# Test model
ollama run llama3.2 "Hello, how are you?"
```

## Test with CognitiveOS

```bash
python main.py
```

```
You: Hi, I'm Alice!
Assistant: Hello Alice! Nice to meet you...
```

## Troubleshooting

### Connection Refused

```
ConnectionError: Connection refused to http://localhost:11434
```

**Solution:** Start Ollama server:
```bash
ollama serve
```

### Model Not Found

```
Error: model 'llama3.2' not found
```

**Solution:** Download the model:
```bash
ollama pull llama3.2
```

### Slow Responses

- Use smaller model (`llama3.2` instead of `llama3.2:7b`)
- Reduce `RETRIEVAL_TOP_K` to inject less context
- Ensure sufficient RAM

### Poor Extraction Quality

Smaller models may miss entities. Try:
- Larger model (`llama3.2:7b`)
- Be more explicit in messages
- Lower `DUPLICATE_THRESHOLD`

## Remote Ollama

To use Ollama on a different machine:

```ini
OLLAMA_BASE_URL=http://192.168.1.100:11434
```

Ensure the server allows remote connections:
```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

## GPU Acceleration

Ollama uses GPU automatically if available:
- NVIDIA: CUDA support
- macOS: Metal support
- AMD: ROCm support (Linux)

Check GPU usage:
```bash
# NVIDIA
nvidia-smi

# Ollama logs show GPU detection
ollama serve
```

## See Also

- [Configuration Reference](../getting-started/configuration.md)
- [Troubleshooting](../troubleshooting.md)
