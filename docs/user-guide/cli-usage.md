# CLI Usage

The console interface provides an interactive way to use CognitiveOS.

## Starting the Console

```bash
python main.py
```

You'll see:
```
🧠 CognitiveOS Console
Type 'quit' to exit, 'stats' for memory statistics

You:
```

## Commands

| Command | Description |
|---------|-------------|
| `quit` | Exit the console |
| `stats` | Show memory statistics |

## Conversation Example

```
You: Hi! I'm Alice and I work at Anthropic.
Assistant: Nice to meet you, Alice! It's great to hear you're working at Anthropic...

You: I specialize in AI safety and RLHF.
Assistant: That's fascinating! RLHF is such an important technique...

You: stats
📊 Memory Statistics
────────────────────
Nodes: 4
Edges: 3
Storage: JSON (data/memory.json)

You: What do you know about me?
Assistant: Based on our conversation, I know that you're Alice, you work at Anthropic,
and you specialize in AI safety research, particularly RLHF...

You: quit
Goodbye!
```

## Tips

- **Be explicit** - "My name is Alice" extracts better than "I'm Alice"
- **Provide context** - "I work at Anthropic as an AI researcher" gives richer data
- **Check stats** - Use `stats` to see how many entities are stored

## Verbose Mode

For debugging, set `LOG_LEVEL=DEBUG` in your `.env` file to see:
- Retrieved context
- Extracted entities
- Storage operations

## See Also

- [Quick Start](../getting-started/quickstart.md)
- [Configuration](../getting-started/configuration.md)
- [Web UI](web-ui.md)
