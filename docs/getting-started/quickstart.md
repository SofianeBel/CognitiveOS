# Quick Start

Get your first memory-enabled conversation running in 5 minutes.

## Prerequisites

Make sure you've completed the [Installation](installation.md) guide.

## 1. Start the Console Interface

```bash
python main.py
```

You'll see:
```
🧠 CognitiveOS Console
Type 'quit' to exit, 'stats' for memory statistics

You:
```

## 2. Have a Conversation

Try introducing yourself:

```
You: Hi! I'm Alice and I work at Anthropic on AI safety research.
```

The system will:
1. **Retrieve context** - Search for relevant memories (none yet)
2. **Generate response** - Use GPT-4o to respond
3. **Extract entities** - Identify "Alice" (Person), "Anthropic" (Organization), "AI safety" (Concept)
4. **Store memories** - Save entities and relations to the graph

Response:
```
Assistant: Nice to meet you, Alice! It's great to hear you're working on AI safety
at Anthropic. That's fascinating and important work. What aspects of AI safety
are you focusing on?
```

## 3. Add More Information

Continue the conversation:

```
You: I specialize in RLHF and I live in San Francisco.
```

More entities extracted:
- "RLHF" (Skill/Concept)
- "San Francisco" (Location)
- Relations: Alice WORKS_AT Anthropic, Alice LIVES_IN San Francisco, Alice LEARNED RLHF

## 4. Test Memory Retrieval

Ask about what you've shared:

```
You: What do you know about me?
```

Response:
```
Assistant: Based on our conversation, I know that you're Alice, and you work at
Anthropic focusing on AI safety research. You specialize in RLHF (Reinforcement
Learning from Human Feedback) and you live in San Francisco.
```

## 5. Check Memory Statistics

Type `stats` to see the knowledge graph state:

```
You: stats
```

Output:
```
📊 Memory Statistics
────────────────────
Nodes: 5
Edges: 4
Storage: JSON (data/memory.json)
```

## 6. Exit

Type `quit` to exit:

```
You: quit
```

## Verify Data Storage

Your memories are stored in `data/memory.json`. You can inspect it:

```bash
cat data/memory.json
```

Example content:
```json
{
  "nodes": {
    "alice_123": {
      "id": "alice_123",
      "label": "Person",
      "name": "Alice",
      "description": "Works at Anthropic on AI safety"
    },
    "anthropic_456": {
      "id": "anthropic_456",
      "label": "Organization",
      "name": "Anthropic"
    }
  },
  "edges": [
    {
      "source": "alice_123",
      "target": "anthropic_456",
      "relation": "WORKS_AT"
    }
  ]
}
```

## Try the Web Interface

For a visual experience with graph visualization:

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser to see:

- Chat interface with memory
- Interactive knowledge graph (PyVis)
- Memory statistics

## What's Next?

- [Configuration](configuration.md) - Customize storage, LLM, and retrieval
- [CLI Usage](../user-guide/cli-usage.md) - Learn all console commands
- [Web UI](../user-guide/web-ui.md) - Explore the Streamlit interface
- [Local LLM](../user-guide/local-llm.md) - Use Ollama for privacy
- [Architecture](../architecture/overview.md) - Understand how it works
