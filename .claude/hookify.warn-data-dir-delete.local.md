---
name: warn-data-dir-delete
enabled: true
event: bash
pattern: rm.*data/
action: warn
---

**Deleting files in data directory!**

You're about to delete files from the `data/` directory which contains:
- `memory.json` - JSON memory storage
- `memory.db` - SQLite memory database

**Before proceeding:**
- Confirm this is intentional
- Consider backing up the data first
- Check if the memory graph has important information

This could result in permanent loss of CognitiveOS memory data.
