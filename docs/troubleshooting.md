# Troubleshooting

Common issues and their solutions.

## Installation Issues

### `ModuleNotFoundError: No module named 'xxx'`

**Cause:** Virtual environment not activated or dependencies not installed.

**Solution:**

=== "Windows"
    ```powershell
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

=== "macOS/Linux"
    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ```

---

### sqlite-vec build fails on Windows

**Error:**
```
error: Microsoft Visual C++ 14.0 or greater is required
```

**Solutions:**

1. **Install Visual Studio Build Tools:**
   - Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Install "Desktop development with C++"
   - Retry installation

2. **Use JSON storage instead:**
   ```ini
   # In .env
   STORAGE_BACKEND=json
   ```

---

### `pip install` hangs or times out

**Cause:** Network issues or slow PyPI mirrors.

**Solution:**
```bash
pip install -r requirements.txt --timeout 120 -i https://pypi.org/simple/
```

---

## Configuration Issues

### `OPENAI_API_KEY not found`

**Error:**
```
ValueError: OPENAI_API_KEY environment variable is required
```

**Solutions:**

1. **Check .env file exists:**
   ```bash
   cat .env | grep OPENAI
   ```

2. **Create .env from example:**
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

3. **Verify format (no quotes needed):**
   ```ini
   # Correct
   OPENAI_API_KEY=sk-your-key-here

   # Wrong
   OPENAI_API_KEY="sk-your-key-here"
   ```

---

### Ollama connection refused

**Error:**
```
ConnectionError: Connection refused to http://localhost:11434
```

**Solutions:**

1. **Start Ollama server:**
   ```bash
   ollama serve
   ```

2. **Check URL matches config:**
   ```ini
   OLLAMA_BASE_URL=http://localhost:11434
   ```

3. **Verify model is downloaded:**
   ```bash
   ollama list
   ollama pull llama3.2
   ```

---

### Invalid configuration value

**Error:**
```
ValueError: RETRIEVAL_TOP_K must be a positive integer
```

**Solution:** Check .env values are correct types:
```ini
# Correct
RETRIEVAL_TOP_K=10
SIMILARITY_THRESHOLD=0.7

# Wrong
RETRIEVAL_TOP_K=ten
SIMILARITY_THRESHOLD=high
```

---

## Runtime Issues

### Embedding model download slow

**Symptom:** First run hangs at "Loading embedding model..."

**Cause:** Downloading `all-MiniLM-L6-v2` (~90MB).

**Solution:** Wait for download to complete. Subsequent runs use cached model.

**Manual download:**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

---

### Out of memory error

**Error:**
```
torch.cuda.OutOfMemoryError
# or
MemoryError
```

**Solutions:**

1. **Use smaller Ollama model:**
   ```ini
   OLLAMA_MODEL=llama3.2  # 3B, not 7B
   ```

2. **Reduce retrieval size:**
   ```ini
   RETRIEVAL_TOP_K=5
   ```

3. **Use JSON backend (less memory):**
   ```ini
   STORAGE_BACKEND=json
   ```

---

### SQLite database locked

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes accessing SQLite simultaneously.

**Solutions:**

1. **Close other instances:**
   - Stop Streamlit if running console
   - Check for zombie processes

2. **Use JSON for concurrent access:**
   ```ini
   STORAGE_BACKEND=json
   ```

---

### `sqlite3.OperationalError: no such module: vec0`

**Cause:** sqlite-vec extension not loaded.

**Solutions:**

1. **Reinstall sqlite-vec:**
   ```bash
   pip uninstall sqlite-vec
   pip install sqlite-vec --no-cache-dir
   ```

2. **Fall back to JSON:**
   ```ini
   STORAGE_BACKEND=json
   ```

---

## LLM Issues

### OpenAI API rate limit

**Error:**
```
openai.RateLimitError: Rate limit reached
```

**Solutions:**

1. **Wait and retry** - Rate limits reset after ~1 minute

2. **Reduce request frequency:**
   - Add delays between messages
   - Reduce `RETRIEVAL_TOP_K` (fewer tokens)

3. **Check usage dashboard:**
   - [OpenAI Usage](https://platform.openai.com/usage)

---

### OpenAI API key invalid

**Error:**
```
openai.AuthenticationError: Invalid API key
```

**Solutions:**

1. **Verify key at OpenAI:**
   - [API Keys](https://platform.openai.com/api-keys)

2. **Check for extra whitespace:**
   ```ini
   # No trailing spaces
   OPENAI_API_KEY=sk-your-key-here
   ```

3. **Regenerate key if compromised**

---

### Ollama model not found

**Error:**
```
ollama._types.ResponseError: model 'llama3.2' not found
```

**Solution:**
```bash
# List available models
ollama list

# Download model
ollama pull llama3.2
```

---

### Poor extraction quality

**Symptoms:**
- Missing entities
- Wrong entity types
- Spurious relations

**Solutions:**

1. **Use larger model:**
   ```ini
   # OpenAI
   # Uses gpt-4o by default, which is good

   # Ollama - use 7B+ model
   OLLAMA_MODEL=llama3.2:7b
   ```

2. **Be more explicit in conversation:**
   - "My name is Alice" (clear)
   - "I'm Alice" (may miss)

3. **Lower duplicate threshold:**
   ```ini
   DUPLICATE_THRESHOLD=0.80
   ```

---

## Data Issues

### Memory file not found

**Error:**
```
FileNotFoundError: data/memory.json not found
```

**Solution:** The file is created automatically on first run. Ensure `data/` directory exists:
```bash
mkdir -p data
```

---

### Corrupted JSON file

**Symptoms:**
- `json.JSONDecodeError`
- Partial data loss

**Solutions:**

1. **Restore from backup:**
   ```bash
   cp data/memory.json.backup data/memory.json
   ```

2. **Start fresh:**
   ```bash
   rm data/memory.json
   # File recreated on next run
   ```

---

### SQLite database corrupted

**Symptoms:**
- `sqlite3.DatabaseError`
- Strange query results

**Solutions:**

1. **Try integrity check:**
   ```bash
   sqlite3 data/memory.db "PRAGMA integrity_check;"
   ```

2. **Restore from backup:**
   ```bash
   cp data/memory.db.backup data/memory.db
   ```

3. **Export and recreate:**
   ```bash
   # If partially readable
   sqlite3 data/memory.db ".dump" > backup.sql
   rm data/memory.db
   sqlite3 data/memory.db < backup.sql
   ```

---

### Migration fails

**Error during `python -m src.memory.migrate`:**

**Solutions:**

1. **Backup first:**
   ```bash
   cp data/memory.json data/memory.json.backup
   ```

2. **Check JSON validity:**
   ```bash
   python -c "import json; json.load(open('data/memory.json'))"
   ```

3. **Migrate in steps:**
   - Export entities
   - Create fresh SQLite
   - Import entities

---

## Streamlit Issues

### Streamlit won't start

**Error:**
```
streamlit: command not found
```

**Solution:**
```bash
pip install streamlit
# Or use python module
python -m streamlit run app.py
```

---

### Port already in use

**Error:**
```
OSError: [Errno 98] Address already in use
```

**Solution:**
```bash
# Use different port
streamlit run app.py --server.port 8502

# Or kill existing process
# Windows
netstat -ano | findstr :8501
taskkill /PID <pid> /F

# Linux/macOS
lsof -i :8501
kill <pid>
```

---

### Graph visualization not loading

**Symptoms:**
- PyVis graph shows blank
- "Loading..." forever

**Solutions:**

1. **Check memory has data:**
   - Run `stats` in console
   - Ensure nodes > 0

2. **Try smaller graph:**
   - Filter by entity type
   - Reduce displayed nodes

3. **Browser console errors:**
   - Open browser DevTools (F12)
   - Check for JavaScript errors

---

## Debug Mode

Enable debug logging to troubleshoot:

```ini
LOG_LEVEL=DEBUG
```

This shows:
- Retrieved context details
- Entity extraction results
- Storage operations
- API calls

---

## Getting Help

If your issue isn't listed:

1. **Search existing issues:**
   - [GitHub Issues](https://github.com/sifly/CognitiveOS/issues)

2. **Create new issue with:**
   - Error message (full traceback)
   - Steps to reproduce
   - Environment (OS, Python version)
   - Configuration (redact API keys)

3. **Check logs:**
   ```bash
   # Run with debug logging
   LOG_LEVEL=DEBUG python main.py 2>&1 | tee debug.log
   ```
