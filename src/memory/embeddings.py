"""Embedding service for semantic similarity."""

from sentence_transformers import SentenceTransformer
from typing import List, Union, Optional
import numpy as np
import logging
import threading

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton service for generating and comparing embeddings."""

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None
    _loading: bool = False
    _load_lock: threading.Lock = threading.Lock()
    _ready_event: threading.Event = threading.Event()

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model, waiting for background load if in progress."""
        if self._model is not None:
            return self._model

        # Wait for background loading if in progress
        if self._loading:
            logger.debug("Waiting for background model loading...")
            self._ready_event.wait()
            return self._model

        # Load synchronously if not already loading
        with self._load_lock:
            if self._model is None:
                self._load_model()
        return self._model

    def _load_model(self) -> None:
        """Internal method to load the model."""
        model_name = settings().embedding_model
        logger.info(f"Loading embedding model: {model_name}")
        self._model = SentenceTransformer(model_name)
        logger.info(f"Model loaded. Embedding dimension: {self._model.get_sentence_embedding_dimension()}")
        self._ready_event.set()

    def warmup(self) -> None:
        """
        Pre-load the embedding model in the background.

        Call this at application startup to avoid cold start latency.
        """
        if self._model is not None or self._loading:
            return

        with self._load_lock:
            if self._model is not None or self._loading:
                return
            self._loading = True

        def _background_load():
            try:
                self._load_model()
                logger.info("Embedding model warmed up in background")
            except Exception as e:
                logger.error(f"Background model loading failed: {e}")
            finally:
                self._loading = False

        thread = threading.Thread(target=_background_load, daemon=True)
        thread.start()
        logger.info("Started background embedding model warmup")

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._model is not None

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            text: Single string or list of strings to embed

        Returns:
            Normalized embedding(s) as numpy array
        """
        return self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True
        )

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for a batch of texts efficiently.

        Args:
            texts: List of strings to embed
            batch_size: Number of texts to process at once

        Returns:
            Normalized embeddings as numpy array
        """
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 100,
            batch_size=batch_size,
            convert_to_numpy=True
        )

    def similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Since embeddings are normalized, this is just a dot product.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between -1 and 1
        """
        return float(np.dot(embedding1, embedding2))

    def batch_similarity(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute similarity between a query and all corpus embeddings.

        Args:
            query_embedding: Single query embedding
            corpus_embeddings: Matrix of corpus embeddings

        Returns:
            Array of similarity scores
        """
        return np.dot(corpus_embeddings, query_embedding)

    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        corpus_embeddings: np.ndarray,
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find the most similar embeddings in a corpus.

        Args:
            query_embedding: Query embedding vector
            corpus_embeddings: Matrix of corpus embeddings
            top_k: Number of top results to return

        Returns:
            List of (index, score) tuples sorted by similarity
        """
        scores = self.batch_similarity(query_embedding, corpus_embeddings)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices]


# Global singleton instance
embedding_service = EmbeddingService()
