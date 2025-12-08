"""Streamlit web application for CognitiveOS."""

import streamlit as st
import streamlit.components.v1 as components
from typing import Optional
import logging

from src.config import settings
from src.memory.graph import MemoryGraph
from src.graph_loop import CognitiveLoop
from src.ui.graph_viz import render_memory_graph, get_entity_type_colors, create_legend_html
from src.consolidation.engine import ConsolidationEngine
from src.agents.llm_factory import LLMFactory
from src.memory.embeddings import embedding_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="CognitiveOS",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        padding: 10px;
    }
    .stats-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .legend-item {
        display: flex;
        align-items: center;
        margin: 5px 0;
    }
    .legend-color {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        margin-right: 8px;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    # Start warming up embedding model in background immediately
    if "warmup_started" not in st.session_state:
        embedding_service.warmup()
        st.session_state.warmup_started = True

    if "cognitive_loop" not in st.session_state:
        st.session_state.cognitive_loop = CognitiveLoop()

    if "memory" not in st.session_state:
        # Use the memory from the cognitive loop
        st.session_state.memory = st.session_state.cognitive_loop.memory

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "graph_filter" not in st.session_state:
        st.session_state.graph_filter = None

    if "graph_search" not in st.session_state:
        st.session_state.graph_search = ""


def render_sidebar():
    """Render the sidebar with graph and controls."""
    with st.sidebar:
        st.title("🧠 Memory Graph")

        # Memory statistics
        stats = st.session_state.memory.get_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Nodes", stats["total_nodes"])
        with col2:
            st.metric("Edges", stats["total_edges"])

        # Storage backend indicator
        backend = stats.get("storage_backend", "json")
        st.caption(f"Storage: {backend.upper()}")

        st.divider()

        # Graph controls
        st.subheader("Graph Controls")

        # Entity type filter
        entity_types = list(get_entity_type_colors().keys())
        selected_types = st.multiselect(
            "Filter by type",
            options=entity_types,
            default=None,
            placeholder="All types"
        )
        st.session_state.graph_filter = selected_types if selected_types else None

        # Search box
        search = st.text_input(
            "Search nodes",
            value=st.session_state.graph_search,
            placeholder="Search by name..."
        )
        st.session_state.graph_search = search

        # Physics toggle
        physics = st.checkbox("Enable physics", value=True)

        # Refresh button
        if st.button("🔄 Refresh Graph", use_container_width=True):
            st.rerun()

        st.divider()

        # Render graph
        if stats["total_nodes"] > 0:
            graph_html = render_memory_graph(
                st.session_state.memory,
                height="400px",
                filter_types=st.session_state.graph_filter,
                search_term=st.session_state.graph_search if st.session_state.graph_search else None,
                physics_enabled=physics
            )
            components.html(graph_html, height=420, scrolling=True)
        else:
            st.info("No memories yet. Start chatting to build your memory graph!")

        st.divider()

        # Legend
        st.subheader("Legend")
        colors = get_entity_type_colors()
        for entity_type, color in colors.items():
            count = stats.get("node_types", {}).get(entity_type, 0)
            st.markdown(
                f'<div class="legend-item">'
                f'<div class="legend-color" style="background-color: {color};"></div>'
                f'{entity_type} ({count})'
                f'</div>',
                unsafe_allow_html=True
            )


def render_chat():
    """Render the chat interface."""
    st.title("CognitiveOS Chat")
    st.caption("Your AI assistant with infinite memory")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("What's on your mind?"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_message(prompt)
                st.markdown(response)

        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Refresh to update graph
        st.rerun()


def process_message(user_message: str) -> str:
    """
    Process a user message through the cognitive loop.

    Args:
        user_message: The user's input message

    Returns:
        The assistant's response
    """
    try:
        # Run through cognitive loop
        loop = st.session_state.cognitive_loop

        # Use the chat method from CognitiveLoop
        response = loop.chat(user_message)

        # Update memory reference in session state
        st.session_state.memory = loop.memory

        return response

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return f"I encountered an error: {str(e)}"


def render_stats_panel():
    """Render detailed statistics panel."""
    with st.expander("📊 Memory Statistics", expanded=False):
        stats = st.session_state.memory.get_stats()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Nodes", stats["total_nodes"])

        with col2:
            st.metric("Total Edges", stats["total_edges"])

        with col3:
            backend = stats.get("storage_backend", "json")
            st.metric("Storage", backend.upper())

        with col4:
            provider_info = LLMFactory.get_provider_info()
            st.metric("LLM Provider", provider_info["provider"].upper())

        # Node types breakdown
        if stats.get("node_types"):
            st.subheader("Nodes by Type")
            for node_type, count in stats["node_types"].items():
                st.progress(
                    count / max(stats["total_nodes"], 1),
                    text=f"{node_type}: {count}"
                )

        # Relation types breakdown
        if stats.get("relation_types"):
            st.subheader("Relations by Type")
            for rel_type, count in stats["relation_types"].items():
                st.progress(
                    count / max(stats["total_edges"], 1),
                    text=f"{rel_type}: {count}"
                )


def render_consolidation_panel():
    """Render the memory consolidation panel."""
    with st.expander("🧹 Memory Consolidation", expanded=False):
        st.write("Optimize your memory graph by merging duplicates and removing stale memories.")

        stats = st.session_state.memory.get_stats()

        if stats["total_nodes"] == 0:
            st.info("No memories to consolidate yet.")
            return

        # Get consolidation candidates
        engine = ConsolidationEngine(st.session_state.memory)

        col1, col2 = st.columns(2)

        with col1:
            duplicate_threshold = st.slider(
                "Duplicate Similarity Threshold",
                min_value=0.7,
                max_value=0.99,
                value=settings().duplicate_merge_threshold,
                step=0.01,
                help="Nodes with similarity above this will be merged"
            )

        with col2:
            prune_days = st.slider(
                "Prune After (days inactive)",
                min_value=7,
                max_value=90,
                value=settings().prune_inactive_days,
                step=1,
                help="Prune nodes inactive for longer than this"
            )

        # Preview button
        if st.button("Preview Changes", use_container_width=True):
            with st.spinner("Analyzing memory..."):
                result = engine.run_full_consolidation(
                    dry_run=True,
                    merge_threshold=duplicate_threshold,
                    prune_days=prune_days
                )

                st.session_state.consolidation_preview = result

        # Show preview if available
        if "consolidation_preview" in st.session_state:
            result = st.session_state.consolidation_preview

            st.subheader("Preview Results")

            # Duplicates
            if result.duplicates_merged:
                st.write(f"**Duplicates to merge:** {len(result.duplicates_merged)}")
                for merge in result.duplicates_merged[:5]:
                    st.write(f"- {', '.join(merge.merged_names)} → **{merge.primary_name}** (similarity: {merge.similarity:.2f})")
                if len(result.duplicates_merged) > 5:
                    st.write(f"*...and {len(result.duplicates_merged) - 5} more*")
            else:
                st.write("*No duplicates found*")

            # Contradictions
            if result.contradictions_found:
                st.warning(f"**Contradictions found:** {len(result.contradictions_found)}")
                for c in result.contradictions_found[:3]:
                    st.write(f"- {c.source_name} ↔ {c.target_name}: {c.relations}")
            else:
                st.write("*No contradictions found*")

            # Prune candidates
            if result.nodes_pruned:
                st.write(f"**Nodes to prune:** {len(result.nodes_pruned)}")
                for name in result.nodes_pruned[:5]:
                    st.write(f"- ~~{name}~~")
                if len(result.nodes_pruned) > 5:
                    st.write(f"*...and {len(result.nodes_pruned) - 5} more*")
            else:
                st.write("*No nodes to prune*")

            # Apply button
            st.divider()
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Apply Changes", type="primary", use_container_width=True):
                    with st.spinner("Consolidating memory..."):
                        final_result = engine.run_full_consolidation(
                            dry_run=False,
                            merge_threshold=duplicate_threshold,
                            prune_days=prune_days
                        )

                        # Update memory reference
                        st.session_state.memory = st.session_state.cognitive_loop.memory

                        # Clear preview
                        del st.session_state.consolidation_preview

                        st.success(
                            f"Consolidation complete!\n"
                            f"Nodes: {final_result.total_nodes_before} → {final_result.total_nodes_after}\n"
                            f"Edges: {final_result.total_edges_before} → {final_result.total_edges_after}"
                        )
                        st.rerun()

            with col2:
                if st.button("Cancel", use_container_width=True):
                    del st.session_state.consolidation_preview
                    st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Render sidebar with graph
    render_sidebar()

    # Main content area
    render_chat()

    # Stats panel at the bottom
    render_stats_panel()

    # Consolidation panel
    render_consolidation_panel()

    # Footer
    st.divider()
    st.caption("CognitiveOS - Local-First Memory System for LLMs")


if __name__ == "__main__":
    main()
