"""LangGraph-based conversation loop with memory."""

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import logging
import os

from src.config import settings
from src.memory.graph import MemoryGraph
from src.agents.extractor import ExtractionAgent
from src.agents.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """State for the conversation graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    context: str
    extraction_result: dict
    user_input: str


class CognitiveLoop:
    """
    Main conversation loop with memory integration.

    Uses LangGraph to orchestrate:
    1. Context retrieval from memory
    2. Response generation with context
    3. Memory storage from conversation
    """

    def __init__(self, memory_path: Optional[str] = None):
        """
        Initialize the cognitive loop.

        Args:
            memory_path: Optional custom path for memory storage
        """
        self.memory = MemoryGraph(filepath=memory_path)
        self.extractor = ExtractionAgent()
        self.llm = LLMFactory.create_chat_llm(temperature=0.7)
        self.graph = self._build_graph()

        # Debug mode for memory retrieval visibility
        self.debug_memory = os.getenv("DEBUG_MEMORY", "false").lower() == "true"

        config = settings()
        logger.info(
            f"CognitiveLoop initialized (provider={config.llm_provider}, "
            f"debug_memory={self.debug_memory})"
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph conversation loop."""
        builder = StateGraph(ConversationState)

        # Add nodes
        builder.add_node("retrieve_context", self._retrieve_context)
        builder.add_node("generate_response", self._generate_response)
        builder.add_node("store_memory", self._store_memory)

        # Add edges: linear flow for now
        builder.add_edge(START, "retrieve_context")
        builder.add_edge("retrieve_context", "generate_response")
        builder.add_edge("generate_response", "store_memory")
        builder.add_edge("store_memory", END)

        return builder.compile()

    def _retrieve_context(self, state: ConversationState) -> dict:
        """
        Node 1: Retrieve relevant context from memory.

        Searches the memory graph for entities and facts relevant
        to the user's input.
        """
        user_input = state["user_input"]
        logger.debug(f"Retrieving context for: {user_input[:50]}...")

        context_items = self.memory.get_context(user_input)
        context_str = self.memory.format_context_for_llm(context_items)

        if context_items:
            logger.info(f"Retrieved {len(context_items)} relevant memories")
        else:
            logger.debug("No relevant memories found")

        # Debug output for memory retrieval visibility
        if self.debug_memory:
            print(f"\n[DEBUG_MEMORY] Query: {user_input}")
            print(f"[DEBUG_MEMORY] Retrieved {len(context_items)} items:")
            for item in context_items:
                relevance = item.get('relevance', 0)
                print(f"[DEBUG_MEMORY]   - {item['entity']} ({item['type']}): {relevance:.3f}")
            if not context_items:
                print("[DEBUG_MEMORY]   (no memories found above threshold)")

        return {"context": context_str}

    def _generate_response(self, state: ConversationState) -> dict:
        """
        Node 2: Generate LLM response with memory context.

        Injects retrieved context into the system prompt to
        personalize the response.
        """
        user_input = state["user_input"]
        context = state["context"]

        # Count retrieved memories for transparency
        memory_count = 0
        if context and context != "No relevant memories found.":
            memory_count = context.count("\n- ")

        system_content = f"""You are a helpful assistant with access to a personal knowledge graph.

======================================================
RELEVANT MEMORIES (Retrieved: {memory_count} items)
======================================================
{context}
======================================================

IMPORTANT INSTRUCTIONS:
1. You MUST use the memories above when they are relevant to the user's question
2. Reference specific facts naturally without saying "I remember"
3. If memories contradict general knowledge, trust the memories (they are personalized)
4. If no relevant memories exist, provide general helpful assistance

Now respond to the user's query:"""

        system_message = SystemMessage(content=system_content)
        human_message = HumanMessage(content=user_input)

        logger.debug("Generating response...")
        response = self.llm.invoke([system_message, human_message])
        logger.debug(f"Response generated: {response.content[:100]}...")

        return {
            "messages": [
                HumanMessage(content=user_input),
                response
            ]
        }

    def _store_memory(self, state: ConversationState) -> dict:
        """
        Node 3: Extract and store new facts from conversation.

        Analyzes the user's input to extract entities and relations,
        then stores them in the memory graph.
        """
        user_input = state["user_input"]

        # Extract entities and relations
        extraction = self.extractor.extract(user_input)

        # Store in graph if we extracted anything
        if extraction.has_content:
            result = self.memory.process_extraction(extraction)
            logger.info(
                f"Stored: {len(result['added_nodes'])} nodes, "
                f"{len(result['added_edges'])} edges, "
                f"{len(result['merged_nodes'])} merged"
            )
        else:
            result = {
                "added_nodes": [],
                "added_edges": [],
                "merged_nodes": []
            }
            logger.debug("No facts to store")

        return {"extraction_result": result}

    def chat(self, user_input: str) -> str:
        """
        Main chat interface.

        Args:
            user_input: User's message

        Returns:
            Assistant's response
        """
        initial_state: ConversationState = {
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
        """Get memory statistics."""
        return self.memory.get_stats()

    def get_last_extraction(self, state_result: dict) -> dict:
        """Get the extraction result from the last chat."""
        return state_result.get("extraction_result", {})
