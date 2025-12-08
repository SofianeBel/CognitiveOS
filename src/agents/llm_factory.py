"""LLM Factory for creating provider-agnostic LLM instances."""

from typing import Optional
import logging

from langchain_openai import ChatOpenAI

from src.config import settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """
    Factory for creating LLM instances based on configuration.

    Supports:
    - OpenAI (GPT-4o) for cloud-based inference
    - Ollama (Llama 3.2) for local inference

    The provider is selected via the LLM_PROVIDER environment variable.
    """

    @staticmethod
    def create_chat_llm(temperature: float = 0.7):
        """
        Create an LLM for chat/response generation.

        Args:
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)

        Returns:
            ChatOpenAI or ChatOllama instance
        """
        config = settings()

        if config.llm_provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                llm = ChatOllama(
                    model=config.ollama_model,
                    base_url=config.ollama_base_url,
                    temperature=temperature
                )
                logger.info(f"Created Ollama chat LLM: {config.ollama_model}")
                return llm
            except ImportError:
                logger.warning(
                    "langchain-ollama not installed. "
                    "Install with: pip install langchain-ollama"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to create Ollama LLM: {e}")
                raise
        else:
            llm = ChatOpenAI(
                model="gpt-4o",
                api_key=config.openai_api_key,
                temperature=temperature
            )
            logger.info("Created OpenAI chat LLM: gpt-4o")
            return llm

    @staticmethod
    def create_extraction_llm():
        """
        Create an LLM for entity extraction (structured output).

        Uses temperature=0 for deterministic extraction.

        Returns:
            ChatOpenAI or ChatOllama instance configured for extraction
        """
        config = settings()

        if config.llm_provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                llm = ChatOllama(
                    model=config.ollama_model,
                    base_url=config.ollama_base_url,
                    temperature=0,
                    format="json"
                )
                logger.info(f"Created Ollama extraction LLM: {config.ollama_model}")
                return llm
            except ImportError:
                logger.warning(
                    "langchain-ollama not installed. "
                    "Install with: pip install langchain-ollama"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to create Ollama LLM: {e}")
                raise
        else:
            llm = ChatOpenAI(
                model="gpt-4o",
                api_key=config.openai_api_key,
                temperature=0
            )
            logger.info("Created OpenAI extraction LLM: gpt-4o")
            return llm

    @staticmethod
    def get_structured_output_method() -> str:
        """
        Get the structured output method for the current provider.

        - OpenAI: Uses function_calling
        - Ollama: Uses json_mode

        Returns:
            Method name for with_structured_output()
        """
        config = settings()
        if config.llm_provider == "ollama":
            return "json_mode"
        return "function_calling"

    @staticmethod
    def is_ollama_available() -> bool:
        """
        Check if Ollama service is available.

        Returns:
            True if Ollama is running and responding
        """
        config = settings()
        if config.llm_provider != "ollama":
            return False

        try:
            import requests
            response = requests.get(
                f"{config.ollama_base_url}/api/tags",
                timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def get_provider_info() -> dict:
        """
        Get information about the current LLM provider.

        Returns:
            Dict with provider details
        """
        config = settings()

        info = {
            "provider": config.llm_provider,
            "model": None,
            "available": False
        }

        if config.llm_provider == "ollama":
            info["model"] = config.ollama_model
            info["base_url"] = config.ollama_base_url
            info["available"] = LLMFactory.is_ollama_available()
        else:
            info["model"] = "gpt-4o"
            info["available"] = bool(config.openai_api_key)

        return info
