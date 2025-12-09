"""Tests for the memory module."""

import pytest
import tempfile
import os
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestNodeModel:
    """Tests for the Node model."""

    def test_node_creation(self):
        """Test basic node creation."""
        from src.memory.models import Node

        node = Node(label="Person", name="Alice")
        assert node.name == "Alice"
        assert node.label == "Person"
        assert node.id is not None
        assert node.embedding is None
        assert node.metadata.access_count == 1

    def test_node_with_description(self):
        """Test node with description."""
        from src.memory.models import Node

        node = Node(
            label="Concept",
            name="Python",
            description="A programming language"
        )
        assert node.description == "A programming language"

    def test_node_touch(self):
        """Test node access tracking."""
        from src.memory.models import Node

        node = Node(label="Person", name="Bob")
        original_count = node.metadata.access_count

        node.touch()
        assert node.metadata.access_count == original_count + 1


class TestEdgeModel:
    """Tests for the Edge model."""

    def test_edge_creation(self):
        """Test basic edge creation."""
        from src.memory.models import Edge

        edge = Edge(
            source="node1",
            target="node2",
            relation="KNOWS"
        )
        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.relation == "KNOWS"
        assert edge.id is not None


class TestExtractionResult:
    """Tests for the ExtractionResult model."""

    def test_empty_result(self):
        """Test empty extraction result."""
        from src.memory.models import ExtractionResult

        result = ExtractionResult()
        assert result.has_content is False
        assert result.get_entity_names() == []

    def test_result_with_entities(self):
        """Test extraction result with entities."""
        from src.memory.models import ExtractionResult, Node

        entities = [
            Node(label="Person", name="Alice"),
            Node(label="Organization", name="Google")
        ]
        result = ExtractionResult(entities=entities)

        assert result.has_content is True
        assert "Alice" in result.get_entity_names()
        assert "Google" in result.get_entity_names()


class TestMemoryGraph:
    """Tests for the MemoryGraph class."""

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

    def test_graph_initialization(self, temp_memory_file):
        """Test graph initialization."""
        # Set environment variable for config
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph

        graph = MemoryGraph(filepath=temp_memory_file)
        assert graph.nodes_data == {}
        assert graph.edges_data == {}

    def test_add_node(self, temp_memory_file):
        """Test adding a node."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph
        from src.memory.models import Node

        graph = MemoryGraph(filepath=temp_memory_file)

        node = Node(label="Person", name="Test User")
        added = graph.add_node(node, check_duplicate=False)

        assert added.id in graph.nodes_data
        assert graph.nodes_data[added.id].name == "Test User"

    def test_get_stats(self, temp_memory_file):
        """Test getting graph statistics."""
        os.environ['OPENAI_API_KEY'] = 'test-key'

        from src.memory.graph import MemoryGraph

        graph = MemoryGraph(filepath=temp_memory_file)
        stats = graph.get_stats()

        assert 'total_nodes' in stats
        assert 'total_edges' in stats
        assert stats['total_nodes'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
