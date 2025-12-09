---
name: warn-env-file-edit
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.env
action: warn
---

**Editing environment file!**

You're modifying a `.env` file which may contain sensitive credentials.

**Reminders:**
- Ensure `.env` is in `.gitignore`
- Never commit real API keys or secrets
- Use `.env.example` for template values
- Consider using environment variables instead of hardcoding

Proceed carefully with sensitive data.
