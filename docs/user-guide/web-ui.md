# Web UI

CognitiveOS includes a Streamlit web interface with interactive graph visualization.

## Starting the Web UI

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Features

### Chat Interface

The main panel provides a chat interface similar to the console:

- Type messages in the input box
- View conversation history
- Memories are extracted automatically

### Graph Visualization

The sidebar shows an interactive PyVis graph:

- **Nodes** - Entities (color-coded by type)
- **Edges** - Relationships between entities
- **Zoom/Pan** - Navigate the graph
- **Click** - Select nodes for details

### Memory Statistics

View real-time stats:
- Total nodes
- Total edges
- Storage backend
- Last update time

## Configuration

### Custom Port

```bash
streamlit run app.py --server.port 8502
```

### Headless Mode

For server deployment:
```bash
streamlit run app.py --server.headless true
```

## Limitations

- **Single user** - Not designed for concurrent access
- **No editing** - Graph is view-only (edit via code)
- **Large graphs** - May be slow with 1000+ nodes

## See Also

- [CLI Usage](cli-usage.md)
- [Configuration](../getting-started/configuration.md)
