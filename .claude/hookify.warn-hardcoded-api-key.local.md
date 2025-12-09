---
name: warn-hardcoded-api-key
enabled: true
event: file
conditions:
  - field: new_text
    operator: regex_match
    pattern: sk-[a-zA-Z0-9]{20,}|api[_-]?key\s*[=:]\s*["'][^"']{10,}
action: warn
---

**Potential API key detected in code!**

You may be hardcoding an API key or secret in the source code.

**Security best practices:**
- Use environment variables: `os.getenv("OPENAI_API_KEY")`
- Store secrets in `.env` files (gitignored)
- Never commit API keys to version control
- Use secret management tools for production

**For CognitiveOS:**
```python
# Good
api_key = os.getenv("OPENAI_API_KEY")

# Bad
api_key = "sk-abc123..."
```
