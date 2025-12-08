"""SQLite database layer with sqlite-vec for vector similarity search."""

import sqlite3
import struct
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
import threading

from src.memory.models import Node, Edge
from src.memory.embeddings import embedding_service
from src.config import settings

logger = logging.getLogger(__name__)


def serialize_float32(vector: List[float]) -> bytes:
    """Serialize a float32 vector to bytes for sqlite-vec."""
    return struct.pack(f'{len(vector)}f', *vector)


def deserialize_float32(data: bytes) -> List[float]:
    """Deserialize bytes back to float32 vector."""
    n = len(data) // 4
    return list(struct.unpack(f'{n}f', data))


class SQLiteMemoryStore:
    """
    SQLite-based memory storage with sqlite-vec for vector similarity.

    Provides:
    - Persistent node/edge storage
    - Vector similarity search via sqlite-vec
    - Thread-safe operations
    - Connection pooling
    """

    # Schema version for future migrations
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the SQLite memory store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or settings().database_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._vec_available = False

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()
        logger.info(f"SQLiteMemoryStore initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row

            # Try to load sqlite-vec extension
            if self._vec_available:
                try:
                    self._local.connection.enable_load_extension(True)
                    import sqlite_vec
                    sqlite_vec.load(self._local.connection)
                except Exception as e:
                    logger.debug(f"Could not load sqlite-vec for this connection: {e}")

        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if sqlite-vec is available
            try:
                conn.enable_load_extension(True)
                import sqlite_vec
                sqlite_vec.load(conn)
                self._vec_available = True
                logger.info("sqlite-vec extension loaded successfully")
            except Exception as e:
                logger.warning(f"sqlite-vec not available, falling back to numpy search: {e}")
                self._vec_available = False

            # Create schema version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            # Create nodes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    importance_score REAL DEFAULT 0.5,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'conversation'
                )
            """)

            # Create edges table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    description TEXT,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL DEFAULT 1.0,
                    valid_from TEXT,
                    valid_to TEXT,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (source_id) REFERENCES nodes(id),
                    FOREIGN KEY (target_id) REFERENCES nodes(id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation)")

            # Create sqlite-vec virtual table if available
            if self._vec_available:
                try:
                    # Check if vec_nodes table exists
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='vec_nodes'
                    """)
                    if not cursor.fetchone():
                        embedding_dim = len(embedding_service.embed("test"))
                        cursor.execute(f"""
                            CREATE VIRTUAL TABLE vec_nodes USING vec0(
                                node_id TEXT PRIMARY KEY,
                                embedding float[{embedding_dim}]
                            )
                        """)
                        logger.info(f"Created vec_nodes virtual table with {embedding_dim}D vectors")
                except Exception as e:
                    logger.warning(f"Could not create vec_nodes table: {e}")
                    self._vec_available = False

            # Set schema version
            cursor.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                          (self.SCHEMA_VERSION,))

            conn.commit()

    def add_node(self, node: Node, check_duplicate: bool = True) -> Node:
        """
        Add a node to the database.

        Args:
            node: Node to add
            check_duplicate: Whether to check for similar existing nodes

        Returns:
            The added node (or existing merged node if duplicate found)
        """
        if check_duplicate:
            existing = self.find_similar_node(node.name, node.description)
            if existing:
                existing_node, score = existing
                logger.debug(
                    f"Found duplicate for '{node.name}' -> "
                    f"'{existing_node.name}' (score={score:.3f})"
                )
                # Update existing node
                self._touch_node(existing_node.id)
                if node.description and not existing_node.description:
                    self._update_node_description(existing_node.id, node.description)
                    existing_node.description = node.description
                return existing_node

        # Generate embedding if not present
        if not node.embedding:
            text = f"{node.name}: {node.description}" if node.description else node.name
            node.embedding = embedding_service.embed(text).tolist()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert into nodes table
            cursor.execute("""
                INSERT OR REPLACE INTO nodes
                (id, label, name, description, embedding, created_at, last_accessed,
                 access_count, importance_score, confidence, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node.id,
                node.label,
                node.name,
                node.description,
                serialize_float32(node.embedding) if node.embedding else None,
                node.metadata.created_at.isoformat(),
                node.metadata.last_accessed.isoformat(),
                node.metadata.access_count,
                node.metadata.importance_score,
                node.metadata.confidence,
                node.metadata.source
            ))

            # Insert into vec_nodes if available
            if self._vec_available and node.embedding:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO vec_nodes (node_id, embedding)
                        VALUES (?, ?)
                    """, (node.id, serialize_float32(node.embedding)))
                except Exception as e:
                    logger.warning(f"Could not insert into vec_nodes: {e}")

            conn.commit()

        logger.debug(f"Added node: {node.name} ({node.label})")
        return node

    def add_edge(self, edge: Edge) -> Edge:
        """
        Add an edge to the database.

        Args:
            edge: Edge to add

        Returns:
            The added edge

        Raises:
            ValueError: If source or target node doesn't exist
        """
        # Verify nodes exist
        source_node = self.get_node(edge.source)
        target_node = self.get_node(edge.target)

        if not source_node:
            raise ValueError(f"Source node {edge.source} not found")
        if not target_node:
            raise ValueError(f"Target node {edge.target} not found")

        # Generate embedding if not present
        if not edge.embedding:
            text = f"{source_node.name} {edge.relation} {target_node.name}"
            if edge.description:
                text += f": {edge.description}"
            edge.embedding = embedding_service.embed(text).tolist()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO edges
                (id, source_id, target_id, relation, description, embedding,
                 created_at, confidence, valid_from, valid_to, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                edge.id,
                edge.source,
                edge.target,
                edge.relation,
                edge.description,
                serialize_float32(edge.embedding) if edge.embedding else None,
                edge.metadata.created_at.isoformat(),
                edge.metadata.confidence,
                edge.validity.start,
                edge.validity.end,
                1
            ))
            conn.commit()

        logger.debug(
            f"Added edge: {source_node.name} --{edge.relation}--> {target_node.name}"
        )
        return edge

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_node(row)

    def get_node_by_name(self, name: str) -> Optional[Node]:
        """Get a node by name (case-insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nodes WHERE LOWER(name) = LOWER(?)",
                (name,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_node(row)

    def get_all_nodes(self) -> List[Node]:
        """Get all nodes from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nodes ORDER BY name")
            return [self._row_to_node(row) for row in cursor.fetchall()]

    def get_all_edges(self) -> List[Edge]:
        """Get all edges from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM edges WHERE is_active = 1")
            return [self._row_to_edge(row) for row in cursor.fetchall()]

    def find_similar_node(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Optional[Tuple[Node, float]]:
        """
        Find an existing node similar to the given one.

        Uses sqlite-vec if available, otherwise falls back to numpy.
        """
        text = f"{name}: {description}" if description else name
        query_embedding = embedding_service.embed(text)
        threshold = settings().duplicate_threshold

        if self._vec_available:
            return self._find_similar_vec(query_embedding, threshold)
        else:
            return self._find_similar_numpy(query_embedding, threshold)

    def _find_similar_vec(
        self,
        query_embedding: Any,
        threshold: float
    ) -> Optional[Tuple[Node, float]]:
        """Find similar node using sqlite-vec."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Use sqlite-vec's distance function
                cursor.execute("""
                    SELECT node_id, distance
                    FROM vec_nodes
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT 1
                """, (serialize_float32(query_embedding.tolist()),))

                row = cursor.fetchone()
                if row:
                    # sqlite-vec returns L2 distance, convert to similarity
                    # similarity = 1 / (1 + distance)
                    distance = row['distance']
                    similarity = 1 / (1 + distance)

                    if similarity >= threshold:
                        node = self.get_node(row['node_id'])
                        if node:
                            return (node, similarity)

                return None
        except Exception as e:
            logger.warning(f"vec search failed, falling back to numpy: {e}")
            return self._find_similar_numpy(query_embedding, threshold)

    def _find_similar_numpy(
        self,
        query_embedding: Any,
        threshold: float
    ) -> Optional[Tuple[Node, float]]:
        """Find similar node using numpy (fallback)."""
        import numpy as np

        best_match = None
        best_score = 0.0

        for node in self.get_all_nodes():
            if node.embedding:
                score = embedding_service.similarity(
                    query_embedding,
                    np.array(node.embedding)
                )
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = node

        return (best_match, best_score) if best_match else None

    def search_similar(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[Node, float]]:
        """
        Search for nodes similar to the query.

        Args:
            query: Search query text
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (node, similarity_score) tuples
        """
        query_embedding = embedding_service.embed(query)

        if self._vec_available:
            return self._search_similar_vec(query_embedding, top_k, threshold)
        else:
            return self._search_similar_numpy(query_embedding, top_k, threshold)

    def _search_similar_vec(
        self,
        query_embedding: Any,
        top_k: int,
        threshold: float
    ) -> List[Tuple[Node, float]]:
        """Search using sqlite-vec."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT node_id, distance
                    FROM vec_nodes
                    WHERE embedding MATCH ?
                    ORDER BY distance
                    LIMIT ?
                """, (serialize_float32(query_embedding.tolist()), top_k * 2))

                results = []
                for row in cursor.fetchall():
                    distance = row['distance']
                    similarity = 1 / (1 + distance)

                    if similarity >= threshold:
                        node = self.get_node(row['node_id'])
                        if node:
                            results.append((node, similarity))

                return results[:top_k]
        except Exception as e:
            logger.warning(f"vec search failed, falling back to numpy: {e}")
            return self._search_similar_numpy(query_embedding, top_k, threshold)

    def _search_similar_numpy(
        self,
        query_embedding: Any,
        top_k: int,
        threshold: float
    ) -> List[Tuple[Node, float]]:
        """Search using numpy (fallback)."""
        import numpy as np

        scored = []
        for node in self.get_all_nodes():
            if node.embedding:
                score = embedding_service.similarity(
                    query_embedding,
                    np.array(node.embedding)
                )
                if score >= threshold:
                    scored.append((node, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_node_neighbors(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all neighbors of a node (incoming and outgoing edges).

        Returns:
            Dict with 'outgoing' and 'incoming' lists of neighbor info
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Outgoing edges
            cursor.execute("""
                SELECT e.*, n.name as target_name, n.label as target_label
                FROM edges e
                JOIN nodes n ON e.target_id = n.id
                WHERE e.source_id = ? AND e.is_active = 1
            """, (node_id,))

            outgoing = []
            for row in cursor.fetchall():
                outgoing.append({
                    'node_id': row['target_id'],
                    'node_name': row['target_name'],
                    'node_label': row['target_label'],
                    'relation': row['relation'],
                    'description': row['description']
                })

            # Incoming edges
            cursor.execute("""
                SELECT e.*, n.name as source_name, n.label as source_label
                FROM edges e
                JOIN nodes n ON e.source_id = n.id
                WHERE e.target_id = ? AND e.is_active = 1
            """, (node_id,))

            incoming = []
            for row in cursor.fetchall():
                incoming.append({
                    'node_id': row['source_id'],
                    'node_name': row['source_name'],
                    'node_label': row['source_label'],
                    'relation': row['relation'],
                    'description': row['description']
                })

            return {'outgoing': outgoing, 'incoming': incoming}

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM edges WHERE is_active = 1")
            total_edges = cursor.fetchone()[0]

            cursor.execute("SELECT label, COUNT(*) as count FROM nodes GROUP BY label")
            node_types = {row['label']: row['count'] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT relation, COUNT(*) as count
                FROM edges WHERE is_active = 1
                GROUP BY relation
            """)
            relation_types = {row['relation']: row['count'] for row in cursor.fetchall()}

            return {
                'total_nodes': total_nodes,
                'total_edges': total_edges,
                'node_types': node_types,
                'relation_types': relation_types,
                'vec_available': self._vec_available
            }

    def _touch_node(self, node_id: str) -> None:
        """Update node access metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE nodes
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), node_id))
            conn.commit()

    def _update_node_description(self, node_id: str, description: str) -> None:
        """Update node description."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE nodes SET description = ? WHERE id = ?",
                (description, node_id)
            )
            conn.commit()

    def _row_to_node(self, row: sqlite3.Row) -> Node:
        """Convert a database row to a Node object."""
        from src.memory.models import NodeMetadata

        embedding = None
        if row['embedding']:
            embedding = deserialize_float32(row['embedding'])

        return Node(
            id=row['id'],
            label=row['label'],
            name=row['name'],
            description=row['description'],
            embedding=embedding,
            metadata=NodeMetadata(
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                last_accessed=datetime.fromisoformat(row['last_accessed']) if row['last_accessed'] else datetime.now(),
                access_count=row['access_count'] or 1,
                importance_score=row['importance_score'] or 0.5,
                confidence=row['confidence'] or 1.0,
                source=row['source'] or 'conversation'
            )
        )

    def _row_to_edge(self, row: sqlite3.Row) -> Edge:
        """Convert a database row to an Edge object."""
        from src.memory.models import EdgeMetadata, EdgeValidity

        embedding = None
        if row['embedding']:
            embedding = deserialize_float32(row['embedding'])

        return Edge(
            id=row['id'],
            source=row['source_id'],
            target=row['target_id'],
            relation=row['relation'],
            description=row['description'],
            embedding=embedding,
            metadata=EdgeMetadata(
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                confidence=row['confidence'] or 1.0
            ),
            validity=EdgeValidity(
                start=row['valid_from'],
                end=row['valid_to']
            )
        )

    def clear(self) -> None:
        """Clear all data from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM edges")
            cursor.execute("DELETE FROM nodes")
            if self._vec_available:
                try:
                    cursor.execute("DELETE FROM vec_nodes")
                except:
                    pass
            conn.commit()
        logger.info("Database cleared")

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
