from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .models import DocumentChunk, RetrievedChunk


class WorkspaceRetriever:
    """
    Local RAG retriever.

    Responsibilities:
    1. Read extracted workspace documents.
    2. Split documents into chunks.
    3. Create embeddings for each chunk.
    4. Store embeddings in FAISS.
    5. Retrieve the most relevant chunks for a question.
    6. Give a small ranking boost when the user's question
       contains words matching the document name.
    """

    def __init__(self, embedding_model=None):

        self.embedding_model_name = (
            embedding_model
            or "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.encoder = None
        self.index = None
        self.chunks: List[DocumentChunk] = []

    def _load_encoder(self):
        """
        Load the embedding model only once.
        """

        if self.encoder is None:

            print(
                f"[RAG] Loading embedding model: "
                f"{self.embedding_model_name}"
            )

            self.encoder = SentenceTransformer(
                self.embedding_model_name
            )

            print("[RAG] Embedding model loaded.")

    def chunk_documents(
        self,
        documents,
        chunk_size=1200,
        overlap=200,
    ):
        """
        Convert document pages into smaller text chunks.

        Example:

        Document
          Page 1
            ↓
          Chunk 1
          Chunk 2
            ↓
          Page 2
            ↓
          Chunk 3
        """

        chunks = []

        for document in documents:

            name = document.get(
                "document",
                "unknown",
            )

            pages = document.get("pages") or []

            for page_number, page_text in enumerate(
                pages,
                start=1,
            ):

                text = (page_text or "").strip()

                if not text:
                    continue

                start = 0
                chunk_number = 0

                while start < len(text):

                    end = start + chunk_size

                    chunk_text = text[
                        start:end
                    ].strip()

                    if chunk_text:

                        chunk_id = (
                            f"{name}:"
                            f"p{page_number}:"
                            f"c{chunk_number}"
                        )

                        chunks.append(
                            DocumentChunk(
                                document=name,
                                page=page_number,
                                text=chunk_text,
                                chunk_id=chunk_id,
                            )
                        )

                    chunk_number += 1

                    next_start = end - overlap

                    if next_start <= start:
                        break

                    start = next_start

        return chunks

    def build(self, documents):
        """
        Build the FAISS vector index.
        """

        self._load_encoder()

        self.chunks = self.chunk_documents(
            documents
        )

        if not self.chunks:

            raise ValueError(
                "No readable document text was found "
                "for Q&A."
            )

        texts = [
            chunk.text
            for chunk in self.chunks
        ]

        embeddings = self.encoder.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        embeddings = np.asarray(
            embeddings,
            dtype="float32",
        )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(embeddings)

        print(
            f"[RAG] Indexed "
            f"{len(self.chunks)} chunks."
        )

    def search(
        self,
        question,
        top_k=5,
    ):
        """
        Search the workspace for evidence relevant
        to the user's question.

        Retrieval uses:

        1. Semantic similarity from FAISS.
        2. Document-name matching.
        3. Re-ranking.
        """

        if self.index is None:

            raise RuntimeError(
                "RAG index has not been built."
            )

        self._load_encoder()

        # -----------------------------------------------------
        # Create embedding for the user's question.
        # -----------------------------------------------------

        query_embedding = self.encoder.encode(
            [question],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype="float32",
        )

        # -----------------------------------------------------
        # Retrieve more candidates than we finally need.
        #
        # Example:
        #
        # top_k = 5
        #
        # Instead of retrieving only 5,
        # retrieve up to 15 candidates first.
        # -----------------------------------------------------

        candidate_k = min(
            max(top_k * 3, 10),
            len(self.chunks),
        )

        scores, indexes = self.index.search(
            query_embedding,
            candidate_k,
        )

        results = []

        # -----------------------------------------------------
        # Clean question words.
        # -----------------------------------------------------

        question_lower = question.lower()

        question_words = {
            word.strip(
                ".,?!:;()[]{}\"'"
            )
            for word in question_lower.split()
            if len(
                word.strip(
                    ".,?!:;()[]{}\"'"
                )
            ) > 3
        }

        # -----------------------------------------------------
        # Score every retrieved candidate.
        # -----------------------------------------------------

        for score, index in zip(
            scores[0],
            indexes[0],
        ):

            if index < 0:
                continue

            chunk = self.chunks[index]

            semantic_score = float(score)

            document_name = (
                chunk.document.lower()
            )

            # -------------------------------------------------
            # Check whether words from the question appear
            # in the document name.
            #
            # Example:
            #
            # Question:
            # "explain customer agreement"
            #
            # Document:
            # "05_customer_agreement.txt"
            #
            # This gets a small ranking boost.
            # -------------------------------------------------

            matching_words = sum(
                1
                for word in question_words
                if word in document_name
            )

            document_boost = (
                0.15 * matching_words
            )

            final_score = (
                semantic_score
                + document_boost
            )

            results.append(
                RetrievedChunk(
                    document=chunk.document,
                    page=chunk.page,
                    text=chunk.text,
                    chunk_id=chunk.chunk_id,
                    score=final_score,
                )
            )

        # -----------------------------------------------------
        # Sort by final score.
        # -----------------------------------------------------

        results.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        # -----------------------------------------------------
        # Return only the requested number.
        # -----------------------------------------------------

        return results[:top_k]