---
name: warn-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf
action: warn
---

**Dangerous rm command detected!**

You're about to run `rm -rf` which permanently deletes files without confirmation.

**Before proceeding:**
- Double-check the path is correct
- Ensure no important data will be lost
- Consider using `rm -ri` for interactive confirmation

This is a warning - the command will still execute if you proceed.
