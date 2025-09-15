import numpy as np
from typing import List, Optional

# from sentence_transformers import SentenceTransformer

from src.utils.logger import LOGGER


class EmbeddingClient:
    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    ):
        self.model_name = model_name
        self.model = None
        # self._load_model()

    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            self.model = SentenceTransformer(self.model_name)
            LOGGER.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            LOGGER.error(f"Failed to load embedding model: {str(e)}")
            raise Exception(f"Could not initialize embedding model: {str(e)}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding vector
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")

            # Clean and normalize text
            cleaned_text = text.strip()

            # Generate embedding
            embedding = self.model.encode(cleaned_text, convert_to_tensor=False)

            # Convert to list of floats
            return embedding.tolist()

        except Exception as e:
            LOGGER.error(f"Failed to generate embedding for text: {str(e)}")
            raise Exception(f"Embedding generation failed: {str(e)}")

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            if not texts:
                return []

            # Clean texts
            cleaned_texts = [
                text.strip() for text in texts if text and text.strip()
            ]

            if not cleaned_texts:
                return []

            # Generate embeddings in batch
            embeddings = self.model.encode(
                cleaned_texts, convert_to_tensor=False
            )

            # Convert to list of lists
            return [embedding.tolist() for embedding in embeddings]

        except Exception as e:
            LOGGER.error(f"Failed to generate batch embeddings: {str(e)}")
            raise Exception(f"Batch embedding generation failed: {str(e)}")

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure result is between 0 and 1
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            LOGGER.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0

    def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        threshold: float = 0.5,
    ) -> Optional[int]:
        """
        Find the most similar embedding from candidates

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embedding vectors
            threshold: Minimum similarity threshold

        Returns:
            Index of most similar candidate, or None if no candidate meets threshold
        """
        try:
            if not candidate_embeddings:
                return None

            best_similarity = -1.0
            best_index = None

            for i, candidate in enumerate(candidate_embeddings):
                similarity = self.calculate_similarity(
                    query_embedding, candidate
                )

                if similarity > best_similarity and similarity >= threshold:
                    best_similarity = similarity
                    best_index = i

            return best_index

        except Exception as e:
            LOGGER.error(f"Failed to find most similar embedding: {str(e)}")
            return None
