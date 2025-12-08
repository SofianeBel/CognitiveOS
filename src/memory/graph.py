"""Memory graph manager using NetworkX with optional SQLite backend."""

import networkx as nx
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Literal
import numpy as np
from datetime import datetime

from src.memory.models import Node, Edge, ExtractionResult
from src.memory.embeddings import embedding_service
from src.config import settings

logger = logging.getLogger(__name__)


class MemoryGraph:
    """
    Graph-based memory storage using NetworkX.

    Provides:
    - Node/edge storage with embeddings
    - Duplicate detection via semantic similarity
    - Context retrieval with graph traversal
    - JSON or SQLite persistence

    Phase 2 adds SQLite backend with sqlite-vec for vector similarity search.
    """

    def __init__(
        self,
        filepath: Optional[str] = None,
        storage_backend: Optional[Literal["json", "sqlite"]] = None
    ):
        """
        Initialize the memory graph.

        Args:
            filepath: Path to storage file (JSON or SQLite database)
            storage_backend: Storage backend to use ("json" or "sqlite")
        """
        self.graph = nx.DiGraph()
        self.storage_backend = storage_backend or settings().storage_backend

        if self.storage_backend == "sqlite":
            self.filepath = filepath or settings().database_path
            from src.memory.database import SQLiteMemoryStore
            self._sqlite_store = SQLiteMemoryStore(self.filepath)
            self.nodes_data: Dict[str, Node] = {}
            self.edges_data: Dict[str, Edge] = {}
            self._load_from_sqlite()
        else:
            self.filepath = filepath or settings().memory_file
            self._sqlite_store = None
            self.nodes_data: Dict[str, Node] = {}
            self.edges_data: Dict[str, Edge] = {}
            self._load()

    def _load(self) -> None:
        """Load graph from JSON file if it exists."""
        path = Path(self.filepath)
        if not path.exists():
            logger.info(f"No existing memory file at {path}, starting fresh")
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for node_data in data.get('nodes', []):
                node = Node(**node_data)
                self.nodes_data[node.id] = node
                self.graph.add_node(node.id, **node.model_dump())

            for edge_data in data.get('edges', []):
                edge = Edge(**edge_data)
                self.edges_data[edge.id] = edge
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    id=edge.id,
                    **edge.model_dump()
                )

            logger.info(
                f"Loaded memory: {len(self.nodes_data)} nodes, "
                f"{len(self.edges_data)} edges"
            )

        except Exception as e:
            logger.error(f"Failed to load memory file: {e}")
            raise

    def _load_from_sqlite(self) -> None:
        """Load graph from SQLite database."""
        if not self._sqlite_store:
            return

        # Load nodes
        for node in self._sqlite_store.get_all_nodes():
            self.nodes_data[node.id] = node
            self.graph.add_node(node.id, **node.model_dump())

        # Load edges
        for edge in self._sqlite_store.get_all_edges():
            self.edges_data[edge.id] = edge
            self.graph.add_edge(
                edge.source,
                edge.target,
                id=edge.id,
                **edge.model_dump()
            )

        logger.info(
            f"Loaded memory from SQLite: {len(self.nodes_data)} nodes, "
            f"{len(self.edges_data)} edges"
        )

    def save(self) -> None:
        """Persist graph to storage (JSON or SQLite)."""
        if self.storage_backend == "sqlite":
            # SQLite saves are handled per-operation, just log
            logger.debug(f"Memory saved to SQLite: {self.filepath}")
            return

        # JSON persistence
        path = Path(self.filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'nodes': [n.model_dump() for n in self.nodes_data.values()],
            'edges': [e.model_dump() for e in self.edges_data.values()],
            'metadata': {
                'saved_at': datetime.now().isoformat(),
                'node_count': len(self.nodes_data),
                'edge_count': len(self.edges_data)
            }
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved memory to {path}")

    def find_similar_node(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Optional[Tuple[Node, float]]:
        """
        Find an existing node similar to the given one.

        Args:
            name: Entity name to search for
            description: Optional description for better matching

        Returns:
            Tuple of (matching_node, similarity_score) or None
        """
        # Use SQLite store if available
        if self._sqlite_store:
            return self._sqlite_store.find_similar_node(name, description)

        if not self.nodes_data:
            return None

        # Combine name and description for embedding
        text = f"{name}: {description}" if description else name
        query_embedding = embedding_service.embed(text)

        best_match = None
        best_score = 0.0
        threshold = settings().duplicate_threshold

        for node in self.nodes_data.values():
            if node.embedding:
                score = embedding_service.similarity(
                    query_embedding,
                    np.array(node.embedding)
                )
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = node

        return (best_match, best_score) if best_match else None

    def add_node(self, node: Node, check_duplicate: bool = True) -> Node:
        """
        Add a node to the graph.

        Args:
            node: Node to add
            check_duplicate: Whether to check for similar existing nodes

        Returns:
            The added node (or existing merged node if duplicate found)
        """
        # Use SQLite store if available
        if self._sqlite_store:
            result = self._sqlite_store.add_node(node, check_duplicate)
            # Keep in-memory graph in sync
            self.nodes_data[result.id] = result
            self.graph.add_node(result.id, **result.model_dump())
            return result

        if check_duplicate:
            existing = self.find_similar_node(node.name, node.description)
            if existing:
                existing_node, score = existing
                logger.debug(
                    f"Found duplicate for '{node.name}' -> "
                    f"'{existing_node.name}' (score={score:.3f})"
                )
                # Update existing node
                existing_node.touch()
                if node.description and not existing_node.description:
                    existing_node.description = node.description
                return existing_node

        # Generate embedding if not present
        if not node.embedding:
            text = f"{node.name}: {node.description}" if node.description else node.name
            node.embedding = embedding_service.embed(text).tolist()

        self.nodes_data[node.id] = node
        self.graph.add_node(node.id, **node.model_dump())
        logger.debug(f"Added node: {node.name} ({node.label})")
        return node

    def add_edge(self, edge: Edge) -> Edge:
        """
        Add an edge to the graph.

        Args:
            edge: Edge to add

        Returns:
            The added edge

        Raises:
            ValueError: If source or target node doesn't exist
        """
        # Use SQLite store if available
        if self._sqlite_store:
            result = self._sqlite_store.add_edge(edge)
            # Keep in-memory graph in sync
            self.edges_data[result.id] = result
            self.graph.add_edge(
                result.source,
                result.target,
                id=result.id,
                **result.model_dump()
            )
            return result

        if edge.source not in self.nodes_data:
            raise ValueError(f"Source node {edge.source} not found")
        if edge.target not in self.nodes_data:
            raise ValueError(f"Target node {edge.target} not found")

        # Generate embedding if not present
        if not edge.embedding:
            source_name = self.nodes_data[edge.source].name
            target_name = self.nodes_data[edge.target].name
            text = f"{source_name} {edge.relation} {target_name}"
            if edge.description:
                text += f": {edge.description}"
            edge.embedding = embedding_service.embed(text).tolist()

        self.edges_data[edge.id] = edge
        self.graph.add_edge(
            edge.source,
            edge.target,
            id=edge.id,
            **edge.model_dump()
        )
        logger.debug(
            f"Added edge: {self.nodes_data[edge.source].name} "
            f"--{edge.relation}--> {self.nodes_data[edge.target].name}"
        )
        return edge

    def process_extraction(self, result: ExtractionResult) -> Dict[str, Any]:
        """
        Process extraction result and add to graph.

        Args:
            result: Extraction result from LLM

        Returns:
            Summary of what was added/merged
        """
        added_nodes = []
        added_edges = []
        merged_nodes = []

        # First pass: add all nodes
        node_id_mapping = {}  # Map extracted node IDs to actual IDs

        for node in result.entities:
            actual_node = self.add_node(node)
            if actual_node.id != node.id:
                merged_nodes.append({
                    'extracted': node.name,
                    'merged_with': actual_node.name
                })
            else:
                added_nodes.append(node.name)
            node_id_mapping[node.id] = actual_node.id

        # Second pass: add edges with corrected IDs
        for edge in result.relations:
            edge.source = node_id_mapping.get(edge.source, edge.source)
            edge.target = node_id_mapping.get(edge.target, edge.target)
            try:
                self.add_edge(edge)
                source_name = self.nodes_data.get(edge.source, Node(label="", name="?")).name
                target_name = self.nodes_data.get(edge.target, Node(label="", name="?")).name
                added_edges.append(f"{source_name} --{edge.relation}--> {target_name}")
            except ValueError as e:
                logger.warning(f"Skipping edge: {e}")

        self.save()

        return {
            'added_nodes': added_nodes,
            'added_edges': added_edges,
            'merged_nodes': merged_nodes
        }

    def get_context(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a query using semantic search.

        Args:
            query: Query string to find relevant context for
            top_k: Number of top results to return

        Returns:
            List of context items with entities and their relations
        """
        if not self.nodes_data:
            return []

        top_k = top_k or settings().retrieval_top_k
        threshold = settings().similarity_threshold

        # Use SQLite store for similarity search if available
        if self._sqlite_store:
            scored_nodes = self._sqlite_store.search_similar(query, top_k, threshold)
        else:
            query_embedding = embedding_service.embed(query)

            # Score all nodes
            scored_nodes = []
            for node in self.nodes_data.values():
                if node.embedding:
                    score = embedding_service.similarity(
                        query_embedding,
                        np.array(node.embedding)
                    )
                    if score >= threshold:
                        scored_nodes.append((node, score))

            # Sort by score and take top-k
            scored_nodes.sort(key=lambda x: x[1], reverse=True)
            scored_nodes = scored_nodes[:top_k]

        # Build context with graph neighbors
        context = []
        for node, score in scored_nodes:
            facts = self._get_node_facts(node)
            context.append({
                'entity': node.name,
                'type': node.label,
                'description': node.description,
                'facts': facts,
                'relevance': score
            })

        return context

    def _get_node_facts(self, node: Node) -> List[Dict[str, Any]]:
        """Get all facts (edges) related to a node."""
        facts = []

        # Outgoing edges
        for neighbor_id in self.graph.neighbors(node.id):
            edge_data = self.graph.edges[node.id, neighbor_id]
            neighbor = self.nodes_data.get(neighbor_id)
            if neighbor:
                facts.append({
                    'relation': edge_data.get('relation'),
                    'target': neighbor.name,
                    'description': edge_data.get('description'),
                    'direction': 'outgoing'
                })

        # Incoming edges
        for predecessor_id in self.graph.predecessors(node.id):
            edge_data = self.graph.edges[predecessor_id, node.id]
            predecessor = self.nodes_data.get(predecessor_id)
            if predecessor:
                facts.append({
                    'relation': f"is {edge_data.get('relation')} by",
                    'target': predecessor.name,
                    'description': edge_data.get('description'),
                    'direction': 'incoming'
                })

        return facts

    def format_context_for_llm(self, context: List[Dict[str, Any]]) -> str:
        """
        Format context into a string for LLM prompt injection.

        Args:
            context: List of context items from get_context()

        Returns:
            Formatted string for LLM consumption
        """
        if not context:
            return "No relevant memories found."

        lines = ["Here's what I remember:"]
        for item in context:
            lines.append(f"\n- {item['entity']} ({item['type']})")
            if item['description']:
                lines.append(f"  Description: {item['description']}")
            for fact in item['facts']:
                if fact['description']:
                    lines.append(
                        f"  {fact['relation']} {fact['target']}: "
                        f"{fact['description']}"
                    )
                else:
                    lines.append(f"  {fact['relation']} {fact['target']}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if self._sqlite_store:
            stats = self._sqlite_store.get_stats()
            stats['storage_backend'] = 'sqlite'
            return stats

        return {
            'total_nodes': len(self.nodes_data),
            'total_edges': len(self.edges_data),
            'node_types': self._count_by_label(),
            'relation_types': self._count_by_relation(),
            'storage_backend': 'json'
        }

    def _count_by_label(self) -> Dict[str, int]:
        """Count nodes by label."""
        counts: Dict[str, int] = {}
        for node in self.nodes_data.values():
            counts[node.label] = counts.get(node.label, 0) + 1
        return counts

    def _count_by_relation(self) -> Dict[str, int]:
        """Count edges by relation type."""
        counts: Dict[str, int] = {}
        for edge in self.edges_data.values():
            counts[edge.relation] = counts.get(edge.relation, 0) + 1
        return counts

    def clear(self) -> None:
        """Clear all data from the graph."""
        if self._sqlite_store:
            self._sqlite_store.clear()

        self.graph.clear()
        self.nodes_data.clear()
        self.edges_data.clear()
        logger.info("Memory graph cleared")
