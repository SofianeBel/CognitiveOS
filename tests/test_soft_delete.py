"""Tests for soft-delete and audit log functionality."""

import pytest
import tempfile
import os
from datetime import datetime

from src.memory.database import SQLiteMemoryStore
from src.memory.models import Node, NodeMetadata


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = SQLiteMemoryStore(path)
    yield store
    store.close()
    os.unlink(path)


class TestSoftDelete:
    """Tests for soft-delete functionality."""

    def test_soft_delete_preserves_node(self, temp_db):
        """Soft-deleted nodes should be preserved in database but not returned by queries."""
        store = temp_db

        # Create and add a node
        node = Node(label="Person", name="Alice")
        node = store.add_node(node, check_duplicate=False)

        # Verify node exists
        assert store.get_node(node.id) is not None

        # Soft-delete the node
        store.soft_delete_node(node.id)

        # Node should not appear in normal queries
        assert store.get_node(node.id) is None
        assert store.get_node_by_name("Alice") is None
        assert len(store.get_all_nodes()) == 0

        # But data should be preserved in database
        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node.id,))
            row = cursor.fetchone()
            assert row is not None
            assert row['deleted_at'] is not None

    def test_soft_delete_with_merge_pointer(self, temp_db):
        """Soft-delete with merged_into should set the pointer correctly."""
        store = temp_db

        # Create two nodes
        alice = Node(label="Person", name="Alice")
        alice = store.add_node(alice, check_duplicate=False)

        alice_dup = Node(label="Person", name="Alice Smith")
        alice_dup = store.add_node(alice_dup, check_duplicate=False)

        # Soft-delete the duplicate with merged_into pointer
        store.soft_delete_node(alice_dup.id, merged_into=alice.id)

        # Original still accessible
        assert store.get_node(alice.id) is not None

        # Merged nodes retrievable
        merged = store.get_merged_nodes(alice.id)
        assert len(merged) == 1
        assert merged[0].name == "Alice Smith"
        assert merged[0].merged_into_id == alice.id

    def test_get_stats_excludes_soft_deleted(self, temp_db):
        """Stats should not count soft-deleted nodes."""
        store = temp_db

        # Add some nodes
        node1 = Node(label="Person", name="Alice")
        node2 = Node(label="Person", name="Bob")
        store.add_node(node1, check_duplicate=False)
        store.add_node(node2, check_duplicate=False)

        stats = store.get_stats()
        assert stats['total_nodes'] == 2

        # Soft-delete one
        store.soft_delete_node(node1.id)

        stats = store.get_stats()
        assert stats['total_nodes'] == 1


class TestAuditLog:
    """Tests for audit log functionality."""

    def test_log_audit_basic(self, temp_db):
        """Should be able to log an audit entry."""
        store = temp_db

        store.log_audit(
            operation="update",
            entity_type="node",
            entity_id="test-id",
            entity_name="Test Node",
            changes={"description": "Added job info"}
        )

        history = store.get_audit_history("test-id")
        assert len(history) == 1
        assert history[0]['operation'] == 'update'
        assert history[0]['entity_type'] == 'node'
        assert history[0]['entity_name'] == 'Test Node'
        assert history[0]['changes'] == {"description": "Added job info"}

    def test_log_audit_with_reason(self, temp_db):
        """Should store reason field correctly."""
        store = temp_db

        store.log_audit(
            operation="delete",
            entity_type="node",
            entity_id="pruned-node",
            entity_name="Old Memory",
            reason="prune_inactive"
        )

        history = store.get_audit_history("pruned-node")
        assert len(history) == 1
        assert history[0]['reason'] == 'prune_inactive'

    def test_log_audit_multiple_entries(self, temp_db):
        """Multiple audit entries should all be returned."""
        store = temp_db
        entity_id = "multi-audit-test"

        store.log_audit(
            operation="create",
            entity_type="node",
            entity_id=entity_id,
            entity_name="Test"
        )

        store.log_audit(
            operation="update",
            entity_type="node",
            entity_id=entity_id,
            entity_name="Test",
            changes={"name": "Test Updated"}
        )

        store.log_audit(
            operation="delete",
            entity_type="node",
            entity_id=entity_id,
            entity_name="Test Updated"
        )

        history = store.get_audit_history(entity_id)
        assert len(history) == 3
        # Check all operations are present (order may vary due to same-second timestamps)
        operations = {h['operation'] for h in history}
        assert operations == {'create', 'update', 'delete'}

    def test_audit_log_empty_for_unknown_entity(self, temp_db):
        """Should return empty list for unknown entity."""
        store = temp_db
        history = store.get_audit_history("nonexistent-id")
        assert history == []


class TestSchemaVersion:
    """Tests for schema version and migration."""

    def test_schema_version_is_2(self, temp_db):
        """Database should be at schema version 2."""
        store = temp_db

        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            assert row[0] == 2

    def test_nodes_table_has_soft_delete_columns(self, temp_db):
        """Nodes table should have deleted_at and merged_into_id columns."""
        store = temp_db

        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(nodes)")
            columns = {row[1] for row in cursor.fetchall()}

            assert 'deleted_at' in columns
            assert 'merged_into_id' in columns

    def test_audit_log_table_exists(self, temp_db):
        """Audit log table should exist with correct structure."""
        store = temp_db

        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(audit_log)")
            columns = {row[1] for row in cursor.fetchall()}

            assert 'id' in columns
            assert 'timestamp' in columns
            assert 'operation' in columns
            assert 'entity_type' in columns
            assert 'entity_id' in columns
            assert 'entity_name' in columns
            assert 'changes' in columns
            assert 'reason' in columns


class TestNodeModel:
    """Tests for Node model with soft-delete fields."""

    def test_node_has_deleted_at_field(self):
        """Node should have deleted_at field."""
        node = Node(label="Person", name="Test")
        assert hasattr(node, 'deleted_at')
        assert node.deleted_at is None

    def test_node_has_merged_into_id_field(self):
        """Node should have merged_into_id field."""
        node = Node(label="Person", name="Test")
        assert hasattr(node, 'merged_into_id')
        assert node.merged_into_id is None

    def test_node_with_deleted_at_set(self):
        """Node can be created with deleted_at set."""
        now = datetime.now()
        node = Node(label="Person", name="Test", deleted_at=now)
        assert node.deleted_at == now

    def test_node_with_merged_into_id_set(self):
        """Node can be created with merged_into_id set."""
        node = Node(label="Person", name="Test", merged_into_id="primary-id")
        assert node.merged_into_id == "primary-id"
