import os

from sentence_transformers import SentenceTransformer


class BGEEmbeddingModel:
    """
    BGE-M3 embedding service.

    Converts document chunks and search queries into vectors that
    can later be stored and searched using PostgreSQL + pgvector.
    """

    def __init__(
        self,
        model_name: str | None = None,
    ):
        self.model_name = model_name or os.getenv(
            "BGE_MODEL",
            "BAAI/bge-m3",
        )

        self.model = SentenceTransformer(
            self.model_name,
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embedding[0].tolist()

    @property
    def dimension(self) -> int:
        return self.model.get_embedding_dimension()
