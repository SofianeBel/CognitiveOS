"""Embedding service for semantic similarity."""

from sentence_transformers import SentenceTransformer
from typing import List, Union, Optional
import numpy as np
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton service for generating and comparing embeddings."""

    _instance: Optional["EmbeddingService"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if self._model is None:
            model_name = settings().embedding_model
            logger.info(f"Loading embedding model: {model_name}")
            self._model = SentenceTransformer(model_name)
            logger.info(f"Model loaded. Embedding dimension: {self._model.get_sentence_embedding_dimension()}")
        return self._model

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
