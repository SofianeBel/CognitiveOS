---
name: warn-print-statements
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: print\(
action: warn
---

**Print statement detected in Python file!**

Consider using proper logging instead of `print()`:

```python
import logging
logger = logging.getLogger(__name__)

# Instead of print("message")
logger.info("message")
logger.debug("debug info")
```

**Why use logging:**
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Output can be redirected to files
- Follows Python best practices
- Already configured via LOG_LEVEL in this project
