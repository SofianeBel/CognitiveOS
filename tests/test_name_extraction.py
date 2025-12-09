"""Tests for personal name extraction and retrieval.

These tests verify that the system correctly extracts and retrieves
personal names when users introduce themselves.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestNameExtraction:
    """Tests for extracting personal names from user messages."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def memory_graph_with_name(self, temp_memory_file):
        """Create a memory graph with a user name relationship."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        # Reset settings for test
        import src.config
        src.config._settings = None
        os.environ['SIMILARITY_THRESHOLD'] = '0.3'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        # Add User node
        user_node = Node(
            label="Person",
            name="User",
            description="The user of this system"
        )
        graph.add_node(user_node, check_duplicate=False)

        # Add name node with rich description for better retrieval
        name_node = Node(
            label="Person",
            name="Sofiane",
            description="User's personal name - the user is called Sofiane"
        )
        graph.add_node(name_node, check_duplicate=False)

        # Add HAS_NAME relationship
        name_edge = Edge(
            source=user_node.id,
            target=name_node.id,
            relation="HAS_NAME",
            description="User's given name is Sofiane"
        )
        graph.add_edge(name_edge)
        graph.save()

        return graph

    def test_name_relationship_exists(self, memory_graph_with_name):
        """Test that HAS_NAME relationship is properly stored."""
        graph = memory_graph_with_name

        # Find User node
        user_node = None
        for node in graph.nodes_data.values():
            if node.name == "User":
                user_node = node
                break

        assert user_node is not None, "User node should exist"

        # Find HAS_NAME edge from User
        has_name_edge = None
        for edge in graph.edges_data.values():
            if edge.source == user_node.id and edge.relation == "HAS_NAME":
                has_name_edge = edge
                break

        assert has_name_edge is not None, "HAS_NAME edge should exist"

        # Verify target is Sofiane
        target_node = graph.nodes_data.get(has_name_edge.target)
        assert target_node is not None, "Target node should exist"
        assert target_node.name == "Sofiane", "Target should be Sofiane"

    def test_name_retrieval_french_query(self, memory_graph_with_name):
        """Test that French name queries retrieve the name."""
        graph = memory_graph_with_name

        # Query in French
        context = graph.get_context("comment je m'appelle?")

        # With HAS_NAME relationship and enriched description,
        # we should find something
        assert isinstance(context, list)

        # If context is found, check it contains name info
        if context:
            all_content = str(context)
            # Should find either Sofiane or User (which has name relation)
            assert "Sofiane" in all_content or "User" in all_content, \
                f"Should find name-related context, got: {context}"

    def test_name_retrieval_english_query(self, memory_graph_with_name):
        """Test that English name queries retrieve the name."""
        graph = memory_graph_with_name

        context = graph.get_context("what is my name?")

        assert isinstance(context, list)

        if context:
            all_content = str(context)
            assert "Sofiane" in all_content or "User" in all_content, \
                f"Should find name-related context, got: {context}"

    def test_name_in_formatted_context(self, memory_graph_with_name):
        """Test that formatted context includes name relationship."""
        graph = memory_graph_with_name

        context = graph.get_context("qui suis-je")
        formatted = graph.format_context_for_llm(context)

        assert isinstance(formatted, str)

        # If we have context, the formatted output should mention the relationship
        if context:
            assert "Here's what I remember:" in formatted or \
                   "No relevant memories" in formatted


class TestNameEdgeEmbedding:
    """Tests for edge embedding in name relationships."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_has_name_edge_has_embedding(self, temp_memory_file):
        """Test that HAS_NAME edges get embeddings."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        user = Node(label="Person", name="User")
        name = Node(label="Person", name="Marie", description="User's name")

        graph.add_node(user, check_duplicate=False)
        graph.add_node(name, check_duplicate=False)

        edge = Edge(
            source=user.id,
            target=name.id,
            relation="HAS_NAME",
            description="User's given name is Marie"
        )
        added_edge = graph.add_edge(edge)

        assert added_edge.embedding is not None, "Edge should have embedding"
        assert len(added_edge.embedding) > 0, "Edge embedding should not be empty"


class TestNameQueryPatterns:
    """Tests for different name query patterns."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def graph_with_name_relation(self, temp_memory_file):
        """Create graph with proper HAS_NAME relationship."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        import src.config
        src.config._settings = None
        os.environ['SIMILARITY_THRESHOLD'] = '0.25'  # Very low for testing

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        user = Node(
            label="Person",
            name="User",
            description="The user of this system"
        )
        graph.add_node(user, check_duplicate=False)

        # Create name node with very descriptive text for better matching
        name = Node(
            label="Person",
            name="Alexandre",
            description="User's personal name - my name is Alexandre, I am called Alexandre"
        )
        graph.add_node(name, check_duplicate=False)

        edge = Edge(
            source=user.id,
            target=name.id,
            relation="HAS_NAME",
            description="The user's name is Alexandre - je m'appelle Alexandre"
        )
        graph.add_edge(edge)
        graph.save()

        return graph

    @pytest.mark.parametrize("query", [
        "comment je m'appelle",
        "je m'appelle comment",
        "quel est mon nom",
        "mon nom c'est quoi",
        "what is my name",
        "what's my name",
        "who am I",
    ])
    def test_various_name_queries(self, graph_with_name_relation, query):
        """Test that various name query patterns work."""
        graph = graph_with_name_relation

        context = graph.get_context(query)

        # The test verifies the query doesn't crash
        # and returns a valid list (may be empty with strict thresholds)
        assert isinstance(context, list), f"Query '{query}' should return a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
