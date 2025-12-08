"""Memory consolidation engine for CognitiveOS.

Handles memory optimization through:
1. Duplicate detection and merging
2. Contradiction detection
3. Inactive memory pruning
"""

from typing import List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import logging

from src.memory.graph import MemoryGraph
from src.memory.embeddings import embedding_service
from src.memory.models import (
    Node, Edge, MergeResult, Contradiction, ConsolidationResult
)
from src.config import settings

logger = logging.getLogger(__name__)

# Labels that should never be pruned
PROTECTED_LABELS = {"User"}

# Opposite relation pairs for contradiction detection
OPPOSITE_RELATIONS = {
    "LIKES": "DISLIKES",
    "DISLIKES": "LIKES",
    "LOVES": "HATES",
    "HATES": "LOVES",
    "TRUSTS": "DISTRUSTS",
    "DISTRUSTS": "TRUSTS",
    "SUPPORTS": "OPPOSES",
    "OPPOSES": "SUPPORTS",
}


class ConsolidationEngine:
    """
    Memory consolidation engine - like sleep for the AI brain.

    Operations:
    1. Duplicate detection and merging (similarity >= threshold)
    2. Contradiction detection and resolution
    3. Inactive memory pruning (>N days, importance < threshold)
    """

    def __init__(self, memory: MemoryGraph):
        """
        Initialize the consolidation engine.

        Args:
            memory: The MemoryGraph to consolidate
        """
        self.memory = memory
        self.config = settings()

    def run_full_consolidation(
        self,
        dry_run: bool = False,
        merge_threshold: float = None,
        prune_days: int = None,
        prune_importance: float = None
    ) -> ConsolidationResult:
        """
        Run a complete consolidation cycle.

        Args:
            dry_run: If True, compute changes but don't apply them
            merge_threshold: Override duplicate merge threshold
            prune_days: Override inactive days threshold
            prune_importance: Override importance threshold for pruning

        Returns:
            ConsolidationResult with details of what was changed
        """
        # Use config values if not overridden
        merge_threshold = merge_threshold or self.config.duplicate_merge_threshold
        prune_days = prune_days or self.config.prune_inactive_days
        prune_importance = prune_importance or self.config.prune_importance_threshold

        result = ConsolidationResult(
            started_at=datetime.now(),
            dry_run=dry_run,
            total_nodes_before=len(self.memory.nodes_data),
            total_edges_before=len(self.memory.edges_data)
        )

        logger.info(
            f"Starting consolidation ({'DRY RUN' if dry_run else 'LIVE'})..."
        )
        logger.info(
            f"  Merge threshold: {merge_threshold}, "
            f"Prune: >{prune_days} days & <{prune_importance} importance"
        )

        # Step 1: Find and merge duplicates
        result.duplicates_merged = self._merge_duplicates(
            threshold=merge_threshold,
            dry_run=dry_run
        )

        # Step 2: Detect contradictions
        result.contradictions_found = self._detect_contradictions()

        # Step 3: Prune inactive nodes
        result.nodes_pruned = self._prune_inactive(
            days_threshold=prune_days,
            importance_threshold=prune_importance,
            dry_run=dry_run
        )

        # Update final counts
        result.total_nodes_after = len(self.memory.nodes_data)
        result.total_edges_after = len(self.memory.edges_data)
        result.completed_at = datetime.now()

        # Save if not dry run
        if not dry_run:
            self.memory.save()

        logger.info(result.summary)
        return result

    def _merge_duplicates(
        self,
        threshold: float = 0.9,
        dry_run: bool = False
    ) -> List[MergeResult]:
        """
        Find and merge duplicate nodes based on embedding similarity.

        Args:
            threshold: Minimum similarity to consider as duplicate
            dry_run: If True, don't actually merge

        Returns:
            List of MergeResult describing what was merged
        """
        merge_results = []
        nodes = list(self.memory.nodes_data.values())

        if len(nodes) < 2:
            return merge_results

        # Build embedding matrix from nodes that have embeddings
        embeddings = []
        valid_nodes = []
        for node in nodes:
            if node.embedding:
                embeddings.append(node.embedding)
                valid_nodes.append(node)

        if len(embeddings) < 2:
            return merge_results

        embeddings_matrix = np.array(embeddings)

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        embeddings_matrix = embeddings_matrix / norms

        # Compute pairwise cosine similarities
        similarities = np.dot(embeddings_matrix, embeddings_matrix.T)

        # Find clusters of duplicates
        merged_ids: Set[str] = set()
        clusters: List[List[int]] = []

        for i in range(len(valid_nodes)):
            if valid_nodes[i].id in merged_ids:
                continue

            # Find all nodes similar to this one
            cluster = [i]
            for j in range(i + 1, len(valid_nodes)):
                if valid_nodes[j].id in merged_ids:
                    continue
                if similarities[i, j] >= threshold:
                    # Must have same label to merge
                    if valid_nodes[i].label == valid_nodes[j].label:
                        cluster.append(j)
                        merged_ids.add(valid_nodes[j].id)

            if len(cluster) > 1:
                clusters.append(cluster)
                merged_ids.add(valid_nodes[i].id)

        # Process each cluster
        for cluster in clusters:
            cluster_nodes = [valid_nodes[idx] for idx in cluster]

            # Select primary node (earliest created)
            cluster_nodes.sort(key=lambda n: n.metadata.created_at)
            primary = cluster_nodes[0]
            secondaries = cluster_nodes[1:]

            # Calculate average similarity within cluster
            cluster_indices = cluster
            cluster_sims = []
            for i, idx_i in enumerate(cluster_indices):
                for idx_j in cluster_indices[i + 1:]:
                    cluster_sims.append(similarities[idx_i, idx_j])
            avg_similarity = np.mean(cluster_sims) if cluster_sims else threshold

            merge_result = MergeResult(
                primary_id=primary.id,
                primary_name=primary.name,
                merged_ids=[n.id for n in secondaries],
                merged_names=[n.name for n in secondaries],
                similarity=float(avg_similarity)
            )
            merge_results.append(merge_result)

            if not dry_run:
                self._execute_merge(primary, secondaries)

            logger.debug(
                f"{'Would merge' if dry_run else 'Merged'}: "
                f"{[n.name for n in secondaries]} -> {primary.name} "
                f"(similarity={avg_similarity:.3f})"
            )

        return merge_results

    def _execute_merge(self, primary: Node, secondaries: List[Node]) -> None:
        """
        Execute the merge of secondary nodes into primary using soft-delete.

        Args:
            primary: The node that will remain
            secondaries: Nodes to merge into primary
        """
        for secondary in secondaries:
            # Merge metadata
            primary.metadata.access_count += secondary.metadata.access_count

            if secondary.metadata.last_accessed > primary.metadata.last_accessed:
                primary.metadata.last_accessed = secondary.metadata.last_accessed

            # Combine descriptions if secondary has one primary doesn't
            if secondary.description and not primary.description:
                primary.description = secondary.description
            elif secondary.description and primary.description:
                # Append if different
                if secondary.description not in primary.description:
                    primary.description = f"{primary.description}; {secondary.description}"

            # Update edges pointing to secondary
            for edge in list(self.memory.edges_data.values()):
                if edge.source == secondary.id:
                    edge.source = primary.id
                if edge.target == secondary.id:
                    edge.target = primary.id

            # Soft-delete secondary node (use SQLite store if available)
            if hasattr(self.memory, '_sqlite_store') and self.memory._sqlite_store:
                self.memory._sqlite_store.log_audit(
                    operation="merge",
                    entity_type="node",
                    entity_id=secondary.id,
                    entity_name=secondary.name,
                    changes={"merged_into": primary.id, "old_name": secondary.name},
                    reason="duplicate_merge"
                )
                self.memory._sqlite_store.soft_delete_node(secondary.id, merged_into=primary.id)
            else:
                # Fallback: hard delete for JSON storage
                if secondary.id in self.memory.nodes_data:
                    del self.memory.nodes_data[secondary.id]

            if secondary.id in self.memory.graph:
                self.memory.graph.remove_node(secondary.id)

        # Regenerate embedding from combined description
        text = f"{primary.name}: {primary.description}" if primary.description else primary.name
        primary.embedding = embedding_service.embed(text).tolist()

        # Update primary in graph
        self.memory.nodes_data[primary.id] = primary
        if primary.id in self.memory.graph:
            self.memory.graph.nodes[primary.id].update(primary.model_dump())

    def _detect_contradictions(self) -> List[Contradiction]:
        """
        Detect contradictory edges in the graph.

        Finds edges with opposite relations between the same entity pairs.

        Returns:
            List of detected Contradictions
        """
        contradictions = []

        # Group edges by (source, target) pair
        edges_by_pair: Dict[Tuple[str, str], List[Edge]] = defaultdict(list)
        for edge in self.memory.edges_data.values():
            # Use sorted tuple to catch both directions
            pair = (edge.source, edge.target)
            edges_by_pair[pair].append(edge)

        # Check each pair for contradictions
        for (source_id, target_id), edges in edges_by_pair.items():
            relations = [e.relation for e in edges]

            for relation in relations:
                if relation in OPPOSITE_RELATIONS:
                    opposite = OPPOSITE_RELATIONS[relation]
                    if opposite in relations:
                        source_node = self.memory.nodes_data.get(source_id)
                        target_node = self.memory.nodes_data.get(target_id)

                        if source_node and target_node:
                            contradiction = Contradiction(
                                source_id=source_id,
                                source_name=source_node.name,
                                target_id=target_id,
                                target_name=target_node.name,
                                relations=relations,
                                resolution="flagged"
                            )
                            contradictions.append(contradiction)

                            logger.warning(
                                f"Contradiction detected: {source_node.name} "
                                f"{relations} {target_node.name}"
                            )
                        break  # Only report once per pair

        return contradictions

    def _prune_inactive(
        self,
        days_threshold: int = 30,
        importance_threshold: float = 0.3,
        dry_run: bool = False
    ) -> List[str]:
        """
        Remove nodes that are inactive and low importance using soft-delete.

        Args:
            days_threshold: Days since last access to consider inactive
            importance_threshold: Maximum importance score to prune
            dry_run: If True, don't actually delete

        Returns:
            List of pruned node names
        """
        pruned_names = []
        cutoff = datetime.now() - timedelta(days=days_threshold)

        for node_id, node in list(self.memory.nodes_data.items()):
            # Skip protected labels
            if node.label in PROTECTED_LABELS:
                continue

            # Check if inactive and low importance
            is_inactive = node.metadata.last_accessed < cutoff
            is_low_importance = node.metadata.importance_score < importance_threshold

            if is_inactive and is_low_importance:
                pruned_names.append(node.name)

                if not dry_run:
                    # Soft-delete node (use SQLite store if available)
                    if hasattr(self.memory, '_sqlite_store') and self.memory._sqlite_store:
                        self.memory._sqlite_store.log_audit(
                            operation="delete",
                            entity_type="node",
                            entity_id=node_id,
                            entity_name=node.name,
                            reason="prune_inactive"
                        )
                        self.memory._sqlite_store.soft_delete_node(node_id)
                    else:
                        # Fallback: hard delete for JSON storage
                        # Remove edges connected to this node
                        edges_to_remove = [
                            edge_id for edge_id, edge in self.memory.edges_data.items()
                            if edge.source == node_id or edge.target == node_id
                        ]
                        for edge_id in edges_to_remove:
                            del self.memory.edges_data[edge_id]
                        del self.memory.nodes_data[node_id]

                    # Remove from in-memory graph
                    if node_id in self.memory.graph:
                        self.memory.graph.remove_node(node_id)

                logger.debug(
                    f"{'Would prune' if dry_run else 'Pruned'}: {node.name} "
                    f"(inactive {days_threshold}+ days, "
                    f"importance={node.metadata.importance_score:.2f})"
                )

        return pruned_names

    def get_duplicate_candidates(
        self,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of potential duplicates without merging.

        Useful for user review before consolidation.

        Args:
            threshold: Minimum similarity (defaults to config value)

        Returns:
            List of dicts with duplicate pair info
        """
        threshold = threshold or self.config.duplicate_merge_threshold
        candidates = []
        nodes = list(self.memory.nodes_data.values())

        if len(nodes) < 2:
            return candidates

        # Build embedding matrix
        embeddings = []
        valid_nodes = []
        for node in nodes:
            if node.embedding:
                embeddings.append(node.embedding)
                valid_nodes.append(node)

        if len(embeddings) < 2:
            return candidates

        embeddings_matrix = np.array(embeddings)
        norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embeddings_matrix = embeddings_matrix / norms
        similarities = np.dot(embeddings_matrix, embeddings_matrix.T)

        # Find pairs above threshold
        seen_pairs = set()
        for i in range(len(valid_nodes)):
            for j in range(i + 1, len(valid_nodes)):
                if similarities[i, j] >= threshold:
                    node_a = valid_nodes[i]
                    node_b = valid_nodes[j]

                    # Only include same-label pairs
                    if node_a.label != node_b.label:
                        continue

                    pair_key = tuple(sorted([node_a.id, node_b.id]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    candidates.append({
                        "node_a": node_a.name,
                        "node_b": node_b.name,
                        "label": node_a.label,
                        "similarity": float(similarities[i, j]),
                        "node_a_created": node_a.metadata.created_at.isoformat(),
                        "node_b_created": node_b.metadata.created_at.isoformat()
                    })

        # Sort by similarity descending
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates

    def get_prune_candidates(
        self,
        days_threshold: int = None,
        importance_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of nodes that would be pruned.

        Useful for user review before consolidation.

        Args:
            days_threshold: Days since last access
            importance_threshold: Maximum importance to prune

        Returns:
            List of dicts with candidate info
        """
        days_threshold = days_threshold or self.config.prune_inactive_days
        importance_threshold = importance_threshold or self.config.prune_importance_threshold

        candidates = []
        cutoff = datetime.now() - timedelta(days=days_threshold)

        for node in self.memory.nodes_data.values():
            if node.label in PROTECTED_LABELS:
                continue

            is_inactive = node.metadata.last_accessed < cutoff
            is_low_importance = node.metadata.importance_score < importance_threshold

            if is_inactive and is_low_importance:
                days_inactive = (datetime.now() - node.metadata.last_accessed).days
                candidates.append({
                    "name": node.name,
                    "label": node.label,
                    "days_inactive": days_inactive,
                    "importance": node.metadata.importance_score,
                    "access_count": node.metadata.access_count,
                    "last_accessed": node.metadata.last_accessed.isoformat()
                })

        # Sort by days inactive descending
        candidates.sort(key=lambda x: x["days_inactive"], reverse=True)
        return candidates
