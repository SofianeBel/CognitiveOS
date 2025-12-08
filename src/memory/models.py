"""Data models for the memory graph system."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
from enum import Enum


class EntityType(str, Enum):
    """Types of entities that can be stored in the graph."""
    PERSON = "Person"
    CONCEPT = "Concept"
    PREFERENCE = "Preference"
    SKILL = "Skill"
    LOCATION = "Location"
    EVENT = "Event"
    ORGANIZATION = "Organization"


class RelationType(str, Enum):
    """Types of relations between entities."""
    KNOWS = "KNOWS"
    LIKES = "LIKES"
    DISLIKES = "DISLIKES"
    WORKS_AT = "WORKS_AT"
    LIVES_IN = "LIVES_IN"
    OWNS = "OWNS"
    LEARNED = "LEARNED"
    CREATED = "CREATED"
    MEMBER_OF = "MEMBER_OF"
    HAS_PROPERTY = "HAS_PROPERTY"
    RELATED_TO = "RELATED_TO"


class NodeMetadata(BaseModel):
    """Metadata associated with a memory node."""
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = 1
    importance_score: float = 0.5
    source: str = "conversation"
    confidence: float = 1.0

    model_config = {"extra": "ignore"}


class Node(BaseModel):
    """A node in the memory graph representing an entity."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str  # Person, Concept, Event, Preference, etc.
    name: str
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)
    # Soft-delete fields for temporal versioning
    deleted_at: Optional[datetime] = None
    merged_into_id: Optional[str] = None

    model_config = {"extra": "ignore"}

    def touch(self) -> None:
        """Update access metadata."""
        self.metadata.last_accessed = datetime.now()
        self.metadata.access_count += 1


class EdgeValidity(BaseModel):
    """Temporal validity of an edge."""
    start: Optional[str] = None
    end: Optional[str] = None  # None means still valid

    model_config = {"extra": "ignore"}


class EdgeMetadata(BaseModel):
    """Metadata associated with a memory edge."""
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 1.0

    model_config = {"extra": "ignore"}


class Edge(BaseModel):
    """An edge in the memory graph representing a relationship."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str  # Node ID
    target: str  # Node ID
    relation: str  # KNOWS, LIKES, WORKS_AT, etc.
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata)
    validity: EdgeValidity = Field(default_factory=EdgeValidity)

    model_config = {"extra": "ignore"}


class ExtractionResult(BaseModel):
    """Result from LLM entity extraction."""
    entities: List[Node] = Field(default_factory=list)
    relations: List[Edge] = Field(default_factory=list)
    reasoning: Optional[str] = None

    model_config = {"extra": "ignore"}

    @property
    def has_content(self) -> bool:
        """Check if extraction produced any results."""
        return bool(self.entities or self.relations)

    def get_entity_names(self) -> List[str]:
        """Get list of extracted entity names."""
        return [e.name for e in self.entities]

    def get_relation_summary(self) -> List[str]:
        """Get human-readable summary of relations."""
        summaries = []
        name_map = {e.id: e.name for e in self.entities}
        for rel in self.relations:
            source_name = name_map.get(rel.source, rel.source)
            target_name = name_map.get(rel.target, rel.target)
            summaries.append(f"{source_name} --{rel.relation}--> {target_name}")
        return summaries


# Phase 3: Consolidation Models

class MergeResult(BaseModel):
    """Result of merging duplicate nodes."""
    primary_id: str
    primary_name: str
    merged_ids: List[str]
    merged_names: List[str]
    similarity: float

    model_config = {"extra": "ignore"}


class Contradiction(BaseModel):
    """Detected contradiction between edges."""
    source_id: str
    source_name: str
    target_id: str
    target_name: str
    relations: List[str]
    resolution: str = "flagged"  # "kept_recent", "flagged", "user_decision"

    model_config = {"extra": "ignore"}


class ConsolidationResult(BaseModel):
    """Result of a consolidation run."""
    started_at: datetime
    completed_at: Optional[datetime] = None
    duplicates_merged: List[MergeResult] = Field(default_factory=list)
    contradictions_found: List[Contradiction] = Field(default_factory=list)
    nodes_pruned: List[str] = Field(default_factory=list)
    total_nodes_before: int = 0
    total_nodes_after: int = 0
    total_edges_before: int = 0
    total_edges_after: int = 0
    dry_run: bool = False

    model_config = {"extra": "ignore"}

    @property
    def summary(self) -> str:
        """Get a human-readable summary of the consolidation."""
        lines = [
            f"Consolidation {'(DRY RUN) ' if self.dry_run else ''}completed:",
            f"  - Duplicates merged: {len(self.duplicates_merged)}",
            f"  - Contradictions found: {len(self.contradictions_found)}",
            f"  - Nodes pruned: {len(self.nodes_pruned)}",
            f"  - Nodes: {self.total_nodes_before} -> {self.total_nodes_after}",
            f"  - Edges: {self.total_edges_before} -> {self.total_edges_after}"
        ]
        return "\n".join(lines)
