# CognitiveOS MVP Implementation Plan

**Version**: 0.1 (Alpha)
**Architecture**: Neuro-Symbolic Local-First
**Objective**: Create infinite, structured memory for LLMs running on consumer laptops

---

## Overview

CognitiveOS is a local-first memory system that enables LLMs to remember user preferences, facts, and relationships across conversations. It uses a "Soft-Graph" architecture combining the structure of knowledge graphs with the flexibility of vector embeddings.

### Core Value Proposition

- **Infinite Memory**: LLM remembers everything you tell it, forever
- **Structured Recall**: Graph-based relationships enable context-aware retrieval
- **Local-First**: All data stays on your laptop, no cloud dependencies
- **Consumer Hardware**: Optimized for standard laptops (8GB RAM minimum)

---

## Technical Stack

| Component | Phase 1 | Phase 2 | Phase 3 |
|-----------|---------|---------|---------|
| **Orchestration** | LangGraph | LangGraph | LangGraph |
| **Intelligence** | GPT-4o API | GPT-4o API | Llama-3.2 3B (Ollama) |
| **Storage** | NetworkX + JSON | SQLite + sqlite-vec | SQLite + sqlite-vec |
| **Embeddings** | sentence-transformers | sentence-transformers | sentence-transformers |
| **Frontend** | Console | Streamlit + PyVis | Streamlit + PyVis |

---

## Data Model

### Node Schema (Memory Entity)

```json
{
  "id": "uuid_v4",
  "label": "Person|Concept|Event|Preference|Skill|Location|Organization",
  "name": "Alice",
  "description": "User's best friend from college",
  "embedding": [0.12, -0.98, ...],
  "metadata": {
    "created_at": "2025-12-08T10:30:00Z",
    "last_accessed": "2025-12-08T14:22:00Z",
    "access_count": 5,
    "importance_score": 0.8,
    "source": "conversation",
    "confidence": 0.95
  }
}
```

### Edge Schema (Relationship)

```json
{
  "id": "uuid_v4",
  "source": "uuid_user",
  "target": "uuid_alice",
  "relation": "KNOWS|LIKES|WORKS_AT|LIVES_IN|OWNS|CREATED|LEARNED",
  "description": "Met at Stanford in 2018, very close friends",
  "embedding": [0.05, 0.23, ...],
  "metadata": {
    "created_at": "2025-12-08T10:30:00Z",
    "confidence": 0.9
  },
  "validity": {
    "start": "2018-09-01",
    "end": null
  }
}
```

### SQLite Schema (Phase 2)

```sql
-- nodes.sql
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    importance_score REAL DEFAULT 0.5,
    source TEXT DEFAULT 'conversation',
    confidence REAL DEFAULT 1.0,
    metadata_json TEXT
);

-- edges.sql
CREATE TABLE edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence REAL DEFAULT 1.0,
    valid_from DATE,
    valid_to DATE,
    is_active INTEGER DEFAULT 1,
    metadata_json TEXT,
    FOREIGN KEY (source_id) REFERENCES nodes(id),
    FOREIGN KEY (target_id) REFERENCES nodes(id)
);

-- vector_nodes.sql (sqlite-vec)
CREATE VIRTUAL TABLE vec_nodes USING vec0(
    node_id TEXT PRIMARY KEY,
    embedding float[384],
    label TEXT,
    +name TEXT,
    +description TEXT
);

-- vector_edges.sql (sqlite-vec)
CREATE VIRTUAL TABLE vec_edges USING vec0(
    edge_id TEXT PRIMARY KEY,
    embedding float[384],
    relation TEXT,
    +description TEXT
);

-- indexes.sql
CREATE INDEX idx_nodes_label ON nodes(label);
CREATE INDEX idx_nodes_name ON nodes(name);
CREATE INDEX idx_nodes_importance ON nodes(importance_score DESC);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_edges_relation ON edges(relation);
```

---

## Phase 1: Dirty Prototype

**Goal**: See memory working in console within 2-3 hours

### Project Structure

```
cognitive-os/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration with Pydantic
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── graph.py           # NetworkX wrapper
│   │   ├── embeddings.py      # sentence-transformers
│   │   └── models.py          # Pydantic data models
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── extractor.py       # Entity extraction agent
│   │   ├── retriever.py       # Context retrieval
│   │   └── responder.py       # Response generation
│   └── graph_loop.py          # LangGraph orchestration
├── data/
│   └── memory.json            # Persisted graph (Phase 1)
├── tests/
│   ├── test_extraction.py
│   ├── test_retrieval.py
│   └── fixtures/
│       └── sample_conversations.json
├── requirements.txt
├── .env.example
└── main.py
```

### Implementation Tasks

#### 1.1 Environment Setup

**File**: `requirements.txt`

```txt
langgraph>=0.2.0
langchain-openai>=0.2.0
networkx>=3.2
sentence-transformers>=2.2.0
pydantic>=2.0
python-dotenv>=1.0
rich>=13.0
```

**File**: `.env.example`

```env
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=all-MiniLM-L6-v2
LOG_LEVEL=INFO
```

#### 1.2 Configuration

**File**: `src/config.py`

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    memory_file: str = Field("data/memory.json", env="MEMORY_FILE")
    retrieval_top_k: int = Field(10, env="RETRIEVAL_TOP_K")
    similarity_threshold: float = Field(0.7, env="SIMILARITY_THRESHOLD")
    duplicate_threshold: float = Field(0.85, env="DUPLICATE_THRESHOLD")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"

settings = Settings()
```

#### 1.3 Data Models

**File**: `src/memory/models.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

class NodeMetadata(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = 1
    importance_score: float = 0.5
    source: str = "conversation"
    confidence: float = 1.0

class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str  # Person, Concept, Event, Preference, etc.
    name: str
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)

class EdgeValidity(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class EdgeMetadata(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 1.0

class Edge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    target: str
    relation: str  # KNOWS, LIKES, WORKS_AT, etc.
    description: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata)
    validity: EdgeValidity = Field(default_factory=EdgeValidity)

class ExtractionResult(BaseModel):
    """Result from LLM entity extraction"""
    entities: List[Node]
    relations: List[Edge]
    reasoning: Optional[str] = None
```

#### 1.4 Embedding Service

**File**: `src/memory/embeddings.py`

```python
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from src.config import settings

class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed(self, text: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for text(s)"""
        return self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False
        )

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        return float(np.dot(embedding1, embedding2))

    def batch_similarity(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray
    ) -> np.ndarray:
        """Compute similarity between query and all corpus embeddings"""
        return np.dot(corpus_embeddings, query_embedding)

embedding_service = EmbeddingService()
```

#### 1.5 Memory Graph Manager

**File**: `src/memory/graph.py`

```python
import networkx as nx
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from datetime import datetime

from src.memory.models import Node, Edge, ExtractionResult
from src.memory.embeddings import embedding_service
from src.config import settings

class MemoryGraph:
    def __init__(self, filepath: Optional[str] = None):
        self.graph = nx.DiGraph()
        self.filepath = filepath or settings.memory_file
        self.nodes_data: Dict[str, Node] = {}
        self.edges_data: Dict[str, Edge] = {}
        self._load()

    def _load(self):
        """Load graph from JSON file"""
        path = Path(self.filepath)
        if path.exists():
            with open(path, 'r') as f:
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

    def save(self):
        """Persist graph to JSON file"""
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

        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def find_similar_node(self, name: str, description: str = None) -> Optional[Tuple[Node, float]]:
        """Find existing node similar to the given one"""
        if not self.nodes_data:
            return None

        # Combine name and description for embedding
        text = f"{name}: {description}" if description else name
        query_embedding = embedding_service.embed(text)

        best_match = None
        best_score = 0.0

        for node in self.nodes_data.values():
            if node.embedding:
                score = embedding_service.similarity(
                    query_embedding,
                    np.array(node.embedding)
                )
                if score > best_score and score >= settings.duplicate_threshold:
                    best_score = score
                    best_match = node

        return (best_match, best_score) if best_match else None

    def add_node(self, node: Node, check_duplicate: bool = True) -> Node:
        """Add node to graph, checking for duplicates"""
        if check_duplicate:
            existing = self.find_similar_node(node.name, node.description)
            if existing:
                existing_node, score = existing
                # Update existing node instead of creating duplicate
                existing_node.metadata.access_count += 1
                existing_node.metadata.last_accessed = datetime.now()
                if node.description and not existing_node.description:
                    existing_node.description = node.description
                return existing_node

        # Generate embedding if not present
        if not node.embedding:
            text = f"{node.name}: {node.description}" if node.description else node.name
            node.embedding = embedding_service.embed(text).tolist()

        self.nodes_data[node.id] = node
        self.graph.add_node(node.id, **node.model_dump())
        return node

    def add_edge(self, edge: Edge) -> Edge:
        """Add edge to graph"""
        # Ensure source and target exist
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
        return edge

    def process_extraction(self, result: ExtractionResult) -> Dict[str, Any]:
        """Process extraction result and add to graph"""
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
                node_id_mapping[node.id] = actual_node.id
            else:
                added_nodes.append(node.name)
                node_id_mapping[node.id] = node.id

        # Second pass: add edges with corrected IDs
        for edge in result.relations:
            edge.source = node_id_mapping.get(edge.source, edge.source)
            edge.target = node_id_mapping.get(edge.target, edge.target)
            try:
                self.add_edge(edge)
                added_edges.append(f"{edge.source} --{edge.relation}--> {edge.target}")
            except ValueError as e:
                pass  # Skip edges with missing nodes

        self.save()

        return {
            'added_nodes': added_nodes,
            'added_edges': added_edges,
            'merged_nodes': merged_nodes
        }

    def get_context(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query using semantic search"""
        if not self.nodes_data:
            return []

        top_k = top_k or settings.retrieval_top_k
        query_embedding = embedding_service.embed(query)

        # Score all nodes
        scored_nodes = []
        for node in self.nodes_data.values():
            if node.embedding:
                score = embedding_service.similarity(
                    query_embedding,
                    np.array(node.embedding)
                )
                if score >= settings.similarity_threshold:
                    scored_nodes.append((node, score))

        # Sort by score
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        top_nodes = scored_nodes[:top_k]

        # Build context with graph neighbors
        context = []
        for node, score in top_nodes:
            # Get related facts
            facts = []
            for neighbor_id in self.graph.neighbors(node.id):
                edge_data = self.graph.edges[node.id, neighbor_id]
                neighbor = self.nodes_data.get(neighbor_id)
                if neighbor:
                    facts.append({
                        'relation': edge_data.get('relation'),
                        'target': neighbor.name,
                        'description': edge_data.get('description')
                    })

            # Get incoming edges
            for predecessor_id in self.graph.predecessors(node.id):
                edge_data = self.graph.edges[predecessor_id, node.id]
                predecessor = self.nodes_data.get(predecessor_id)
                if predecessor:
                    facts.append({
                        'relation': f"is {edge_data.get('relation')} by",
                        'target': predecessor.name,
                        'description': edge_data.get('description')
                    })

            context.append({
                'entity': node.name,
                'type': node.label,
                'description': node.description,
                'facts': facts,
                'relevance': score
            })

        return context

    def format_context_for_llm(self, context: List[Dict[str, Any]]) -> str:
        """Format context into a string for LLM prompt"""
        if not context:
            return "No relevant memories found."

        lines = ["Here's what I remember:"]
        for item in context:
            lines.append(f"\n- {item['entity']} ({item['type']})")
            if item['description']:
                lines.append(f"  Description: {item['description']}")
            for fact in item['facts']:
                if fact['description']:
                    lines.append(f"  {fact['relation']} {fact['target']}: {fact['description']}")
                else:
                    lines.append(f"  {fact['relation']} {fact['target']}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        return {
            'total_nodes': len(self.nodes_data),
            'total_edges': len(self.edges_data),
            'node_types': self._count_by_label(),
            'relation_types': self._count_by_relation()
        }

    def _count_by_label(self) -> Dict[str, int]:
        counts = {}
        for node in self.nodes_data.values():
            counts[node.label] = counts.get(node.label, 0) + 1
        return counts

    def _count_by_relation(self) -> Dict[str, int]:
        counts = {}
        for edge in self.edges_data.values():
            counts[edge.relation] = counts.get(edge.relation, 0) + 1
        return counts
```

#### 1.6 Entity Extraction Agent

**File**: `src/agents/extractor.py`

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import json

from src.config import settings
from src.memory.models import Node, Edge, ExtractionResult

EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction agent for a personal knowledge system.
Your job is to analyze user messages and extract:

1. **Entities**: People, concepts, places, preferences, skills, events, organizations
2. **Relations**: How entities are connected (KNOWS, LIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED, etc.)

## Entity Types
- Person: Names of people (friends, family, colleagues)
- Concept: Abstract ideas, topics, technologies
- Preference: User likes/dislikes, habits
- Skill: Things the user can do or is learning
- Location: Places, cities, addresses
- Event: Past or future events, milestones
- Organization: Companies, schools, groups

## Relation Types
- KNOWS: Personal relationship with someone
- LIKES: Positive preference
- DISLIKES: Negative preference
- WORKS_AT: Employment relationship
- LIVES_IN: Location relationship
- OWNS: Possession
- LEARNED: Skill or knowledge acquisition
- CREATED: Made something
- MEMBER_OF: Group membership
- HAS_PROPERTY: Attribute of something

## Rules
1. Only extract facts that are explicitly stated or strongly implied
2. The "User" entity always exists - extract relationships TO the user
3. Use past tense for historical facts, present for current state
4. Include confidence scores (0.0-1.0) based on how certain you are
5. Skip greetings, small talk, and non-factual content

## Example Input
"I just got a promotion at Google! My friend Alice helped me prepare for the interview."

## Example Output
{
  "entities": [
    {"label": "Person", "name": "User", "description": "The user of this system"},
    {"label": "Organization", "name": "Google", "description": "Tech company where user works"},
    {"label": "Person", "name": "Alice", "description": "User's friend who helped with interview prep"}
  ],
  "relations": [
    {"source": "User", "target": "Google", "relation": "WORKS_AT", "description": "Recently got promoted"},
    {"source": "User", "target": "Alice", "relation": "KNOWS", "description": "Friend who helped with interview preparation"}
  ],
  "reasoning": "Extracted work relationship and friendship based on explicit mentions"
}
"""

class EntityExtraction(BaseModel):
    """Structured output for entity extraction"""
    entities: List[dict] = Field(description="List of extracted entities")
    relations: List[dict] = Field(description="List of extracted relations")
    reasoning: Optional[str] = Field(None, description="Brief explanation of extraction")

class ExtractionAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
            temperature=0
        ).with_structured_output(EntityExtraction)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", "{user_message}")
        ])

        self.chain = self.prompt | self.llm

    def extract(self, user_message: str) -> ExtractionResult:
        """Extract entities and relations from user message"""
        try:
            result = self.chain.invoke({"user_message": user_message})

            # Convert to proper models
            entities = []
            for entity_data in result.entities:
                entities.append(Node(
                    label=entity_data.get('label', 'Concept'),
                    name=entity_data.get('name', ''),
                    description=entity_data.get('description')
                ))

            # Build ID mapping for relations
            name_to_id = {e.name: e.id for e in entities}

            relations = []
            for rel_data in result.relations:
                source_name = rel_data.get('source', '')
                target_name = rel_data.get('target', '')

                # Map names to IDs
                source_id = name_to_id.get(source_name)
                target_id = name_to_id.get(target_name)

                if source_id and target_id:
                    relations.append(Edge(
                        source=source_id,
                        target=target_id,
                        relation=rel_data.get('relation', 'RELATED_TO'),
                        description=rel_data.get('description')
                    ))

            return ExtractionResult(
                entities=entities,
                relations=relations,
                reasoning=result.reasoning
            )

        except Exception as e:
            # Return empty result on failure
            return ExtractionResult(entities=[], relations=[], reasoning=f"Extraction failed: {e}")
```

#### 1.7 LangGraph Orchestration

**File**: `src/graph_loop.py`

```python
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import settings
from src.memory.graph import MemoryGraph
from src.agents.extractor import ExtractionAgent

class ConversationState(TypedDict):
    messages: Annotated[List, add_messages]
    context: str
    extraction_result: dict
    user_input: str

class CognitiveLoop:
    def __init__(self):
        self.memory = MemoryGraph()
        self.extractor = ExtractionAgent()
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.openai_api_key,
            temperature=0.7
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph conversation loop"""
        builder = StateGraph(ConversationState)

        # Add nodes
        builder.add_node("retrieve_context", self._retrieve_context)
        builder.add_node("generate_response", self._generate_response)
        builder.add_node("store_memory", self._store_memory)

        # Add edges
        builder.add_edge(START, "retrieve_context")
        builder.add_edge("retrieve_context", "generate_response")
        builder.add_edge("generate_response", "store_memory")
        builder.add_edge("store_memory", END)

        return builder.compile()

    def _retrieve_context(self, state: ConversationState) -> dict:
        """Node 1: Retrieve relevant context from memory"""
        user_input = state["user_input"]
        context_items = self.memory.get_context(user_input)
        context_str = self.memory.format_context_for_llm(context_items)

        return {"context": context_str}

    def _generate_response(self, state: ConversationState) -> dict:
        """Node 2: Generate LLM response with context"""
        user_input = state["user_input"]
        context = state["context"]

        system_message = SystemMessage(content=f"""You are a helpful assistant with memory capabilities.

{context}

Use this context to personalize your responses. If the user mentions something you remember,
acknowledge it naturally. Don't explicitly say "I remember" - just use the information.""")

        human_message = HumanMessage(content=user_input)

        response = self.llm.invoke([system_message, human_message])

        return {
            "messages": [
                HumanMessage(content=user_input),
                response
            ]
        }

    def _store_memory(self, state: ConversationState) -> dict:
        """Node 3: Extract and store new facts from conversation"""
        user_input = state["user_input"]

        # Extract entities and relations
        extraction = self.extractor.extract(user_input)

        # Store in graph
        if extraction.entities or extraction.relations:
            result = self.memory.process_extraction(extraction)
        else:
            result = {"added_nodes": [], "added_edges": [], "merged_nodes": []}

        return {"extraction_result": result}

    def chat(self, user_input: str) -> str:
        """Main chat interface"""
        initial_state = {
            "messages": [],
            "context": "",
            "extraction_result": {},
            "user_input": user_input
        }

        result = self.graph.invoke(initial_state)

        # Return the assistant's response
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                return msg.content

        return "I'm not sure how to respond to that."

    def get_memory_stats(self) -> dict:
        """Get memory statistics"""
        return self.memory.get_stats()
```

#### 1.8 Main Entry Point

**File**: `main.py`

```python
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.graph_loop import CognitiveLoop

console = Console()

def main():
    console.print(Panel.fit(
        "[bold blue]CognitiveOS[/bold blue] - Local Memory System\n"
        "Type 'quit' to exit, 'stats' to see memory stats",
        title="Welcome"
    ))

    cognitive = CognitiveLoop()

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == 'stats':
                stats = cognitive.get_memory_stats()
                console.print(Panel(
                    f"Nodes: {stats['total_nodes']}\n"
                    f"Edges: {stats['total_edges']}\n"
                    f"Node Types: {stats['node_types']}\n"
                    f"Relations: {stats['relation_types']}",
                    title="Memory Stats"
                ))
                continue

            response = cognitive.chat(user_input)
            console.print(f"\n[bold blue]Assistant:[/bold blue] {response}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
```

---

## Phase 2: Persistence & Vectors

**Goal**: Graph persists across sessions, semantic search works, visualization available

### Additional Tasks

#### 2.1 SQLite Integration

**File**: `src/memory/database.py`

```python
import sqlite3
import sqlite_vec
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import numpy as np

from src.memory.models import Node, Edge
from src.memory.embeddings import embedding_service
from src.config import settings

class SQLiteMemoryStore:
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._setup()

    def _setup(self):
        """Initialize database schema"""
        # Enable sqlite-vec
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        # Create tables
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                importance_score REAL DEFAULT 0.5,
                source TEXT DEFAULT 'conversation',
                confidence REAL DEFAULT 1.0,
                metadata_json TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 1.0,
                valid_from DATE,
                valid_to DATE,
                is_active INTEGER DEFAULT 1,
                metadata_json TEXT,
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);
            CREATE INDEX IF NOT EXISTS idx_nodes_name ON nodes(name);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
        """)

        # Create vector tables
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_nodes USING vec0(
                node_id TEXT PRIMARY KEY,
                embedding float[384],
                label TEXT,
                +name TEXT,
                +description TEXT
            )
        """)

        self.conn.commit()

    def add_node(self, node: Node) -> str:
        """Insert or update a node"""
        # Generate embedding if needed
        if not node.embedding:
            text = f"{node.name}: {node.description}" if node.description else node.name
            node.embedding = embedding_service.embed(text).tolist()

        # Insert into nodes table
        self.conn.execute("""
            INSERT OR REPLACE INTO nodes
            (id, label, name, description, importance_score, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (node.id, node.label, node.name, node.description,
              node.metadata.importance_score, node.metadata.confidence))

        # Insert into vector table
        from sqlite_vec import serialize_float32
        embedding_blob = serialize_float32(node.embedding)

        self.conn.execute("""
            INSERT OR REPLACE INTO vec_nodes
            (node_id, embedding, label, name, description)
            VALUES (?, ?, ?, ?, ?)
        """, (node.id, embedding_blob, node.label, node.name, node.description))

        self.conn.commit()
        return node.id

    def search_similar(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Semantic search for similar nodes"""
        from sqlite_vec import serialize_float32

        query_embedding = embedding_service.embed(query)
        query_blob = serialize_float32(query_embedding.tolist())

        results = self.conn.execute("""
            SELECT
                node_id,
                name,
                description,
                label,
                distance
            FROM vec_nodes
            WHERE embedding MATCH ?
                AND k = ?
            ORDER BY distance
        """, [query_blob, top_k]).fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "description": r[2],
                "label": r[3],
                "distance": r[4],
                "similarity": 1 - r[4]  # Convert distance to similarity
            }
            for r in results
        ]

    def close(self):
        self.conn.close()
```

#### 2.2 Streamlit UI

**File**: `app.py`

```python
import streamlit as st
from pyvis.network import Network
import tempfile
import os

from src.graph_loop import CognitiveLoop
from src.memory.graph import MemoryGraph

st.set_page_config(page_title="CognitiveOS", layout="wide")

# Initialize session state
if 'cognitive' not in st.session_state:
    st.session_state.cognitive = CognitiveLoop()
if 'messages' not in st.session_state:
    st.session_state.messages = []

def render_graph():
    """Render memory graph using PyVis"""
    memory = st.session_state.cognitive.memory

    if not memory.nodes_data:
        st.info("No memories yet. Start chatting to build your memory graph!")
        return

    net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")
    net.force_atlas_2based()

    # Add nodes
    for node in memory.nodes_data.values():
        color = {
            "Person": "#FF6B6B",
            "Concept": "#4ECDC4",
            "Preference": "#FFE66D",
            "Location": "#95E1D3",
            "Organization": "#F38181",
            "Event": "#AA96DA",
            "Skill": "#FCBAD3"
        }.get(node.label, "#FFFFFF")

        net.add_node(
            node.id,
            label=node.name,
            title=f"{node.label}: {node.description or 'No description'}",
            color=color
        )

    # Add edges
    for edge in memory.edges_data.values():
        net.add_edge(
            edge.source,
            edge.target,
            title=edge.relation,
            label=edge.relation
        )

    # Save and display
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
        net.save_graph(f.name)
        with open(f.name, 'r') as html_file:
            st.components.v1.html(html_file.read(), height=550)
        os.unlink(f.name)

def main():
    st.title("CognitiveOS")
    st.markdown("*Your personal memory companion*")

    # Sidebar with stats and graph
    with st.sidebar:
        st.header("Memory Graph")
        stats = st.session_state.cognitive.get_memory_stats()
        col1, col2 = st.columns(2)
        col1.metric("Nodes", stats['total_nodes'])
        col2.metric("Edges", stats['total_edges'])

        if st.button("Refresh Graph"):
            st.rerun()

        render_graph()

    # Chat interface
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Tell me something..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.cognitive.chat(prompt)
                st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

if __name__ == "__main__":
    main()
```

---

## Phase 3: Consolidation ("Sleep")

**Goal**: Long-term memory optimization, duplicate detection, contradiction resolution

### Consolidation Engine

**File**: `src/consolidation/engine.py`

```python
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

from src.memory.graph import MemoryGraph
from src.memory.embeddings import embedding_service
from src.config import settings

class ConsolidationEngine:
    """
    Handles memory consolidation - like sleep for the AI brain:
    1. Detect duplicate/similar nodes
    2. Find contradictions
    3. Create abstract parent nodes from clusters
    4. Prune inactive memories
    """

    def __init__(self, memory: MemoryGraph):
        self.memory = memory
        self.consolidation_log = []

    def run_full_consolidation(self) -> Dict[str, Any]:
        """Run complete consolidation cycle"""
        results = {
            'started_at': datetime.now().isoformat(),
            'duplicates_merged': [],
            'contradictions_found': [],
            'abstractions_created': [],
            'nodes_pruned': [],
            'total_nodes_before': len(self.memory.nodes_data),
            'total_nodes_after': 0
        }

        # Step 1: Find and merge duplicates
        results['duplicates_merged'] = self._merge_duplicates()

        # Step 2: Detect contradictions
        results['contradictions_found'] = self._detect_contradictions()

        # Step 3: Create abstractions from clusters
        results['abstractions_created'] = self._create_abstractions()

        # Step 4: Prune inactive nodes
        results['nodes_pruned'] = self._prune_inactive()

        results['total_nodes_after'] = len(self.memory.nodes_data)
        results['completed_at'] = datetime.now().isoformat()

        self.memory.save()
        return results

    def _merge_duplicates(self, threshold: float = 0.9) -> List[Dict[str, str]]:
        """Find and merge duplicate nodes based on embedding similarity"""
        merged = []
        nodes = list(self.memory.nodes_data.values())

        # Build embedding matrix
        embeddings = []
        valid_nodes = []
        for node in nodes:
            if node.embedding:
                embeddings.append(node.embedding)
                valid_nodes.append(node)

        if len(embeddings) < 2:
            return merged

        embeddings_matrix = np.array(embeddings)

        # Compute pairwise similarities
        similarities = np.dot(embeddings_matrix, embeddings_matrix.T)

        # Find pairs above threshold
        merged_ids = set()
        for i in range(len(valid_nodes)):
            if valid_nodes[i].id in merged_ids:
                continue
            for j in range(i + 1, len(valid_nodes)):
                if valid_nodes[j].id in merged_ids:
                    continue
                if similarities[i, j] >= threshold:
                    # Merge j into i
                    primary = valid_nodes[i]
                    secondary = valid_nodes[j]

                    # Update primary with info from secondary
                    primary.metadata.access_count += secondary.metadata.access_count
                    if not primary.description and secondary.description:
                        primary.description = secondary.description

                    # Update edges pointing to secondary
                    for edge in list(self.memory.edges_data.values()):
                        if edge.source == secondary.id:
                            edge.source = primary.id
                        if edge.target == secondary.id:
                            edge.target = primary.id

                    # Remove secondary
                    del self.memory.nodes_data[secondary.id]
                    if secondary.id in self.memory.graph:
                        self.memory.graph.remove_node(secondary.id)

                    merged_ids.add(secondary.id)
                    merged.append({
                        'kept': primary.name,
                        'merged': secondary.name,
                        'similarity': float(similarities[i, j])
                    })

        return merged

    def _detect_contradictions(self) -> List[Dict[str, Any]]:
        """Detect potential contradictions in the graph"""
        contradictions = []

        # Find edges with opposite relations
        opposite_relations = {
            'LIKES': 'DISLIKES',
            'DISLIKES': 'LIKES',
            'LOVES': 'HATES',
            'HATES': 'LOVES'
        }

        edges_by_pair = defaultdict(list)
        for edge in self.memory.edges_data.values():
            key = (edge.source, edge.target)
            edges_by_pair[key].append(edge)

        for (source, target), edges in edges_by_pair.items():
            relations = [e.relation for e in edges]
            for rel in relations:
                if rel in opposite_relations and opposite_relations[rel] in relations:
                    source_node = self.memory.nodes_data.get(source)
                    target_node = self.memory.nodes_data.get(target)
                    if source_node and target_node:
                        contradictions.append({
                            'source': source_node.name,
                            'target': target_node.name,
                            'relations': relations,
                            'type': 'opposite_relations'
                        })

        return contradictions

    def _create_abstractions(self, min_cluster_size: int = 3) -> List[Dict[str, Any]]:
        """Create abstract parent nodes from clusters of similar nodes"""
        # Group nodes by label
        nodes_by_label = defaultdict(list)
        for node in self.memory.nodes_data.values():
            if node.embedding:
                nodes_by_label[node.label].append(node)

        abstractions = []

        for label, nodes in nodes_by_label.items():
            if len(nodes) < min_cluster_size:
                continue

            # Simple clustering: find centroid and nodes close to it
            embeddings = np.array([n.embedding for n in nodes])
            centroid = embeddings.mean(axis=0)

            # Find nodes close to centroid
            similarities = np.dot(embeddings, centroid)
            threshold = np.percentile(similarities, 75)

            cluster_nodes = [n for n, sim in zip(nodes, similarities) if sim >= threshold]

            if len(cluster_nodes) >= min_cluster_size:
                # Create abstract node
                names = [n.name for n in cluster_nodes[:5]]
                abstract_name = f"{label} cluster: {', '.join(names)}"

                abstractions.append({
                    'label': label,
                    'abstract_name': abstract_name,
                    'member_count': len(cluster_nodes),
                    'members': [n.name for n in cluster_nodes]
                })

        return abstractions

    def _prune_inactive(self, days_threshold: int = 30) -> List[str]:
        """Remove nodes that haven't been accessed in X days"""
        pruned = []
        cutoff = datetime.now() - timedelta(days=days_threshold)

        for node_id, node in list(self.memory.nodes_data.items()):
            if node.metadata.last_accessed < cutoff:
                # Check if node has low importance
                if node.metadata.importance_score < 0.3:
                    pruned.append(node.name)
                    del self.memory.nodes_data[node_id]
                    if node_id in self.memory.graph:
                        self.memory.graph.remove_node(node_id)

        return pruned
```

---

## Acceptance Criteria

### Phase 1 (Must Have)

- [ ] User can chat with the system via console
- [ ] System extracts entities and relations from conversation
- [ ] Memory persists to JSON file between sessions
- [ ] Context retrieval works for basic queries
- [ ] Duplicate detection prevents fragmented graph
- [ ] >80% precision on entity extraction (10 test conversations)

### Phase 2 (Must Have)

- [ ] SQLite database with sqlite-vec integration
- [ ] Semantic search returns relevant context in <100ms for 10K nodes
- [ ] Streamlit UI displays conversation and graph
- [ ] PyVis visualization is interactive
- [ ] Migration from Phase 1 JSON to Phase 2 SQLite works

### Phase 3 (Should Have)

- [ ] Consolidation detects and merges duplicates
- [ ] Contradiction detection flags conflicting facts
- [ ] Pruning removes stale memories (>30 days inactive, low importance)
- [ ] System works offline with Ollama + Llama-3.2 3B

---

## Risk Analysis

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM extraction quality <80% | High | Medium | Few-shot examples in prompt, manual testing |
| sqlite-vec installation issues | Medium | Medium | Fallback to basic SQLite + numpy similarity |
| NetworkX performance at 10K nodes | Medium | Low | Early migration to SQLite |
| OpenAI API costs | Medium | Medium | Batch extraction, rate limiting |
| Ollama setup complexity | Low | Medium | Clear installation guide, auto-download model |

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [sentence-transformers all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [sqlite-vec GitHub](https://github.com/asg017/sqlite-vec)
- [PyVis Documentation](https://pyvis.readthedocs.io/)
- [NetworkX Documentation](https://networkx.org/)

---

## Next Steps After Plan Approval

1. Create project structure with files listed above
2. Implement Phase 1 core components (2-3 hours)
3. Test with 10 sample conversations
4. Iterate on extraction prompt until >80% precision
5. Begin Phase 2 SQLite migration
