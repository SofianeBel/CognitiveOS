"""Entity extraction agent using LLM."""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from src.config import settings
from src.memory.models import Node, Edge, ExtractionResult
from src.agents.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


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
- HAS_NAME: User's personal name (CRITICAL: use when user says "my name is X", "I'm called X", "je m'appelle X")
- IS_CALLED: Nickname or alternative name
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
- RELATED_TO: General relationship between entities

## Rules
1. Only extract facts that are explicitly stated or strongly implied
2. ALWAYS include "User" as an entity when the user expresses preferences, relationships, or facts about themselves
3. Use past tense for historical facts, present for current state
4. Include confidence scores (0.0-1.0) based on how certain you are
5. Skip greetings, small talk, and non-factual content
6. If the message contains no extractable facts, return empty lists

## Example Input
"I just got a promotion at Google! My friend Alice helped me prepare for the interview."

## Example Output
{{
  "entities": [
    {{"label": "Person", "name": "User", "description": "The user of this system"}},
    {{"label": "Organization", "name": "Google", "description": "Tech company where user works"}},
    {{"label": "Person", "name": "Alice", "description": "User's friend who helped with interview prep"}}
  ],
  "relations": [
    {{"source": "User", "target": "Google", "relation": "WORKS_AT", "description": "Recently got promoted"}},
    {{"source": "User", "target": "Alice", "relation": "KNOWS", "description": "Friend who helped with interview preparation"}}
  ],
  "reasoning": "Extracted work relationship and friendship based on explicit mentions"
}}

## Example Input (Personal name - IMPORTANT)
"Je m'appelle Marie"

## Example Output (Personal name)
{{
  "entities": [
    {{"label": "Person", "name": "User", "description": "The user of this system"}},
    {{"label": "Person", "name": "Marie", "description": "User's personal name"}}
  ],
  "relations": [
    {{"source": "User", "target": "Marie", "relation": "HAS_NAME", "description": "User's given name is Marie"}}
  ],
  "reasoning": "User introduced themselves with their name - this is a HAS_NAME relationship"
}}

## Example Input (English name)
"My name is John and I'm a software developer"

## Example Output (English name)
{{
  "entities": [
    {{"label": "Person", "name": "User", "description": "The user of this system"}},
    {{"label": "Person", "name": "John", "description": "User's personal name"}},
    {{"label": "Skill", "name": "Software Development", "description": "User's profession"}}
  ],
  "relations": [
    {{"source": "User", "target": "John", "relation": "HAS_NAME", "description": "User's given name"}},
    {{"source": "User", "target": "Software Development", "relation": "LEARNED", "description": "User's profession"}}
  ],
  "reasoning": "Extracted user's name and profession from introduction"
}}

## Example Input (No facts)
"Hello! How are you today?"

## Example Output (No facts)
{{
  "entities": [],
  "relations": [],
  "reasoning": "Greeting message with no extractable facts"
}}
"""


class ExtractedEntity(BaseModel):
    """An extracted entity from user message."""
    label: str = Field(description="Entity type: Person, Concept, Preference, Skill, Location, Event, or Organization")
    name: str = Field(description="Name of the entity")
    description: Optional[str] = Field(None, description="Brief description of the entity")


class ExtractedRelation(BaseModel):
    """An extracted relation between entities."""
    source: str = Field(description="Name of the source entity")
    target: str = Field(description="Name of the target entity")
    relation: str = Field(description="Relation type: HAS_NAME, IS_CALLED, KNOWS, LIKES, DISLIKES, WORKS_AT, LIVES_IN, OWNS, LEARNED, CREATED, MEMBER_OF, HAS_PROPERTY, RELATED_TO")
    description: Optional[str] = Field(None, description="Brief description of the relation")


class EntityExtraction(BaseModel):
    """Structured output for entity extraction."""
    entities: List[ExtractedEntity] = Field(
        default_factory=list,
        description="List of extracted entities"
    )
    relations: List[ExtractedRelation] = Field(
        default_factory=list,
        description="List of extracted relations"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of extraction decisions"
    )


class ExtractionAgent:
    """Agent for extracting entities and relations from user messages."""

    def __init__(self):
        """Initialize the extraction agent with LLM."""
        # Get base LLM from factory
        base_llm = LLMFactory.create_extraction_llm()

        # Get the appropriate structured output method
        method = LLMFactory.get_structured_output_method()

        # Create structured output LLM
        self.llm = base_llm.with_structured_output(EntityExtraction, method=method)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", "{user_message}")
        ])

        self.chain = self.prompt | self.llm

        config = settings()
        logger.info(
            f"ExtractionAgent initialized (provider={config.llm_provider})"
        )

    def extract(self, user_message: str) -> ExtractionResult:
        """
        Extract entities and relations from a user message.

        Args:
            user_message: The message to analyze

        Returns:
            ExtractionResult with entities and relations
        """
        try:
            logger.debug(f"Extracting from: {user_message[:100]}...")
            result = self.chain.invoke({"user_message": user_message})

            # Convert ExtractedEntity to Node models
            entities = []
            for entity_data in result.entities:
                entities.append(Node(
                    label=entity_data.label,
                    name=entity_data.name,
                    description=entity_data.description
                ))

            # Build ID mapping for relations (name -> id)
            name_to_id = {e.name: e.id for e in entities}

            # Collect all entity names referenced in relations
            referenced_names = set()
            for rel in result.relations:
                referenced_names.add(rel.source)
                referenced_names.add(rel.target)

            # Auto-create missing entities (especially "User")
            for name in referenced_names:
                if name not in name_to_id:
                    if name == "User":
                        node = Node(
                            label="Person",
                            name="User",
                            description="The user of this system"
                        )
                    else:
                        # Create generic entity for other missing references
                        node = Node(
                            label="Concept",
                            name=name,
                            description=f"Entity referenced in relation"
                        )
                    entities.append(node)
                    name_to_id[name] = node.id
                    logger.info(f"Auto-created missing entity: {name} ({node.label})")

            # Convert ExtractedRelation to Edge models
            relations = []
            for rel_data in result.relations:
                source_name = rel_data.source
                target_name = rel_data.target

                # Map names to IDs
                source_id = name_to_id.get(source_name)
                target_id = name_to_id.get(target_name)

                if source_id and target_id:
                    relations.append(Edge(
                        source=source_id,
                        target=target_id,
                        relation=rel_data.relation,
                        description=rel_data.description
                    ))
                else:
                    logger.warning(
                        f"Skipping relation: {source_name} -> {target_name} "
                        f"(missing entity)"
                    )

            extraction = ExtractionResult(
                entities=entities,
                relations=relations,
                reasoning=result.reasoning
            )

            logger.info(
                f"Extracted {len(entities)} entities, "
                f"{len(relations)} relations"
            )
            if result.reasoning:
                logger.debug(f"Reasoning: {result.reasoning}")

            return extraction

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return ExtractionResult(
                entities=[],
                relations=[],
                reasoning=f"Extraction failed: {e}"
            )
