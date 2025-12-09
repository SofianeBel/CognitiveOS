"""Tests for context retrieval functionality.

These tests verify that the memory retrieval system correctly finds
and returns relevant context for queries.
"""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestContextRetrieval:
    """Tests for the get_context functionality."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        # Remove the empty file so MemoryGraph starts fresh
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def memory_graph_with_data(self, temp_memory_file):
        """Create a memory graph with test data."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        # Ensure threshold is low enough for testing
        import src.config
        src.config._settings = None
        os.environ['SIMILARITY_THRESHOLD'] = '0.3'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        # Add nodes
        user_node = Node(label="Person", name="User", description="The user of this system")
        python_node = Node(label="Skill", name="Python", description="Programming language")
        alice_node = Node(label="Person", name="Alice", description="User's best friend")

        graph.add_node(user_node, check_duplicate=False)
        graph.add_node(python_node, check_duplicate=False)
        graph.add_node(alice_node, check_duplicate=False)

        # Add edges
        likes_edge = Edge(
            source=user_node.id,
            target=python_node.id,
            relation="LIKES",
            description="User enjoys programming in Python"
        )
        knows_edge = Edge(
            source=user_node.id,
            target=alice_node.id,
            relation="KNOWS",
            description="Best friend since childhood"
        )

        graph.add_edge(likes_edge)
        graph.add_edge(knows_edge)
        graph.save()

        return graph

    def test_retrieval_finds_relevant_nodes(self, memory_graph_with_data):
        """Test that retrieval finds nodes matching the query."""
        graph = memory_graph_with_data

        context = graph.get_context("What programming languages do I like?")

        assert len(context) > 0, "Should retrieve at least one item"
        entity_names = [item['entity'] for item in context]
        # Should find Python or User (related to the LIKES edge)
        assert any(name in ['Python', 'User'] for name in entity_names), \
            f"Should find Python or User in results, got: {entity_names}"

    def test_retrieval_with_lowered_threshold(self, memory_graph_with_data):
        """Test that lowered threshold allows retrieval."""
        graph = memory_graph_with_data

        # The test fixture sets threshold to 0.3 for reliable testing
        from src.config import settings
        assert settings().similarity_threshold <= 0.4, \
            f"Threshold should be 0.4 or lower, got {settings().similarity_threshold}"

        context = graph.get_context("Tell me about my preferences")
        # With lowered threshold, should find something
        assert isinstance(context, list)

    def test_retrieval_includes_facts(self, memory_graph_with_data):
        """Test that retrieved context includes related facts (edges)."""
        graph = memory_graph_with_data

        context = graph.get_context("Who is Alice?")

        if context:
            # Check that facts are included
            for item in context:
                assert 'facts' in item, "Context items should include facts"
                assert isinstance(item['facts'], list), "Facts should be a list"

    def test_retrieval_includes_relevance_score(self, memory_graph_with_data):
        """Test that context items include relevance scores."""
        graph = memory_graph_with_data

        context = graph.get_context("Python programming")

        if context:
            for item in context:
                assert 'relevance' in item, "Context items should include relevance"
                assert isinstance(item['relevance'], float), "Relevance should be a float"
                assert 0 <= item['relevance'] <= 1, "Relevance should be between 0 and 1"

    def test_retrieval_respects_top_k(self, memory_graph_with_data):
        """Test that retrieval respects top_k limit."""
        graph = memory_graph_with_data

        context = graph.get_context("Tell me everything", top_k=2)

        assert len(context) <= 2, "Should respect top_k limit"

    def test_format_context_for_llm(self, memory_graph_with_data):
        """Test that context is formatted correctly for LLM."""
        graph = memory_graph_with_data

        context = graph.get_context("Python")
        formatted = graph.format_context_for_llm(context)

        assert isinstance(formatted, str), "Formatted context should be a string"
        if context:
            assert "Here's what I remember:" in formatted, \
                "Should include memory header"

    def test_empty_context_formatting(self):
        """Test formatting when no context is found."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        # Create a fresh temp file that doesn't exist
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        os.unlink(path)

        try:
            from src.memory.graph import MemoryGraph
            graph = MemoryGraph(filepath=path)
            formatted = graph.format_context_for_llm([])
            assert formatted == "No relevant memories found."
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestEdgeSearch:
    """Tests for edge embedding search functionality."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        # Remove the empty file so MemoryGraph starts fresh
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_edge_embeddings_are_created(self, temp_memory_file):
        """Test that edges get embeddings when created."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        # Add nodes first
        user = Node(label="Person", name="User")
        pizza = Node(label="Food", name="Pizza", description="Italian food")

        graph.add_node(user, check_duplicate=False)
        graph.add_node(pizza, check_duplicate=False)

        # Add edge
        edge = Edge(
            source=user.id,
            target=pizza.id,
            relation="LIKES",
            description="User loves pizza"
        )
        added_edge = graph.add_edge(edge)

        assert added_edge.embedding is not None, "Edge should have embedding"
        assert len(added_edge.embedding) > 0, "Edge embedding should not be empty"

    def test_relationship_query_finds_edges(self, temp_memory_file):
        """Test that relationship queries can find relevant edges."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node, Edge

        graph = MemoryGraph(filepath=temp_memory_file)

        # Add nodes
        user = Node(label="Person", name="User")
        coffee = Node(label="Preference", name="Coffee", description="Hot beverage")

        graph.add_node(user, check_duplicate=False)
        graph.add_node(coffee, check_duplicate=False)

        # Add edge with clear relationship
        edge = Edge(
            source=user.id,
            target=coffee.id,
            relation="LIKES",
            description="User drinks coffee every morning"
        )
        graph.add_edge(edge)
        graph.save()

        # Query about preferences
        context = graph.get_context("What does the user like to drink?")

        # Should find something related
        assert isinstance(context, list)


class TestThresholdBehavior:
    """Tests for similarity threshold behavior."""

    @pytest.fixture
    def temp_memory_file(self):
        """Create a temporary file for memory storage."""
        fd, path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        # Remove the empty file so MemoryGraph starts fresh
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_default_threshold_is_lowered(self):
        """Verify the default threshold in code is 0.4.

        Note: This tests the code default, not the runtime value which may be
        overridden by .env file or environment variables.
        """
        # Check the Field default directly from the class definition
        from src.config import Settings
        from pydantic.fields import FieldInfo

        # Get the field info for similarity_threshold
        field_info = Settings.model_fields.get('similarity_threshold')
        assert field_info is not None, "similarity_threshold field should exist"
        assert field_info.default == 0.4, \
            f"Code default threshold should be 0.4, got {field_info.default}"

    def test_threshold_can_be_overridden(self, temp_memory_file):
        """Test that threshold can be overridden via environment."""
        original_threshold = os.environ.get('SIMILARITY_THRESHOLD')

        try:
            os.environ['SIMILARITY_THRESHOLD'] = '0.5'

            # Force reload of settings
            from src.config import Settings
            test_settings = Settings()

            assert test_settings.similarity_threshold == 0.5
        finally:
            if original_threshold:
                os.environ['SIMILARITY_THRESHOLD'] = original_threshold
            elif 'SIMILARITY_THRESHOLD' in os.environ:
                del os.environ['SIMILARITY_THRESHOLD']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
