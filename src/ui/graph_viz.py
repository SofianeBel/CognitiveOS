"""PyVis graph visualization for memory graph."""

from pyvis.network import Network
from typing import Optional, Dict, List, Any
import tempfile
import os

from src.memory.graph import MemoryGraph


# Node colors by entity type
NODE_COLORS = {
    "Person": "#FF6B6B",      # Red
    "Concept": "#4ECDC4",     # Teal
    "Preference": "#FFE66D",  # Yellow
    "Location": "#95E1D3",    # Mint
    "Organization": "#F38181", # Coral
    "Event": "#AA96DA",       # Purple
    "Skill": "#FCBAD3",       # Pink
}

DEFAULT_COLOR = "#808080"  # Gray for unknown types


def render_memory_graph(
    memory: MemoryGraph,
    height: str = "600px",
    width: str = "100%",
    bgcolor: str = "#ffffff",
    font_color: str = "#333333",
    filter_types: Optional[List[str]] = None,
    search_term: Optional[str] = None,
    physics_enabled: bool = True
) -> str:
    """
    Render memory graph as interactive HTML.

    Args:
        memory: MemoryGraph instance to visualize
        height: Height of the visualization
        width: Width of the visualization
        bgcolor: Background color
        font_color: Font color for labels
        filter_types: List of entity types to show (None = all)
        search_term: Highlight nodes matching this term
        physics_enabled: Enable physics-based layout

    Returns:
        HTML string for embedding in Streamlit
    """
    # Create PyVis network
    net = Network(
        height=height,
        width=width,
        bgcolor=bgcolor,
        font_color=font_color,
        directed=True,
        notebook=False,
        select_menu=False,
        filter_menu=False
    )

    # Configure physics
    if physics_enabled:
        net.barnes_hut(
            gravity=-5000,
            central_gravity=0.3,
            spring_length=150,
            spring_strength=0.05,
            damping=0.09
        )
    else:
        net.toggle_physics(False)

    # Track which nodes to include
    included_nodes = set()

    # Add nodes
    for node_id, node in memory.nodes_data.items():
        # Filter by type if specified
        if filter_types and node.label not in filter_types:
            continue

        # Check search term
        matches_search = True
        if search_term:
            search_lower = search_term.lower()
            matches_search = (
                search_lower in node.name.lower() or
                (node.description and search_lower in node.description.lower())
            )

        if not matches_search and search_term:
            continue

        included_nodes.add(node_id)

        # Determine node color
        color = NODE_COLORS.get(node.label, DEFAULT_COLOR)

        # Build tooltip
        title = f"<b>{node.name}</b><br>"
        title += f"Type: {node.label}<br>"
        if node.description:
            title += f"Description: {node.description}<br>"
        title += f"Access count: {node.metadata.access_count}"

        # Determine node size based on access count
        size = min(30, 10 + (node.metadata.access_count * 2))

        # Highlight if matching search
        border_width = 3 if search_term and matches_search else 1

        net.add_node(
            node_id,
            label=node.name,
            title=title,
            color={
                "background": color,
                "border": "#333333",
                "highlight": {
                    "background": color,
                    "border": "#000000"
                }
            },
            size=size,
            borderWidth=border_width,
            font={"size": 14}
        )

    # Add edges
    for edge_id, edge in memory.edges_data.items():
        # Only add edges between included nodes
        if edge.source not in included_nodes or edge.target not in included_nodes:
            continue

        # Build edge tooltip
        source_name = memory.nodes_data.get(edge.source)
        target_name = memory.nodes_data.get(edge.target)
        title = f"{source_name.name if source_name else '?'} "
        title += f"<b>{edge.relation}</b> "
        title += f"{target_name.name if target_name else '?'}"
        if edge.description:
            title += f"<br>{edge.description}"

        net.add_edge(
            edge.source,
            edge.target,
            title=title,
            label=edge.relation,
            arrows="to",
            color={"color": "#666666", "highlight": "#333333"},
            font={"size": 10, "align": "middle"},
            smooth={"type": "curvedCW", "roundness": 0.2}
        )

    # Generate HTML
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            net.save_graph(f.name)
            temp_path = f.name

        # Read the generated HTML
        with open(temp_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # Clean up temp file
        os.unlink(temp_path)

        return html

    except Exception as e:
        return f"<p>Error generating graph: {e}</p>"


def get_entity_type_colors() -> Dict[str, str]:
    """Get the color mapping for entity types."""
    return NODE_COLORS.copy()


def get_graph_stats(memory: MemoryGraph) -> Dict[str, Any]:
    """
    Get statistics for the graph visualization.

    Args:
        memory: MemoryGraph instance

    Returns:
        Dictionary with visualization statistics
    """
    stats = memory.get_stats()

    # Add visualization-specific stats
    stats['colors'] = NODE_COLORS

    return stats


def create_legend_html() -> str:
    """Create HTML for the graph legend."""
    html = '<div style="padding: 10px;">'
    html += '<h4>Entity Types</h4>'

    for entity_type, color in NODE_COLORS.items():
        html += f'''
        <div style="display: flex; align-items: center; margin: 5px 0;">
            <div style="
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background-color: {color};
                margin-right: 8px;
                border: 1px solid #333;
            "></div>
            <span>{entity_type}</span>
        </div>
        '''

    html += '</div>'
    return html
