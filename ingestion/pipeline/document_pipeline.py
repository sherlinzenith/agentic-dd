from pathlib import Path

from database.session import SessionLocal
from ingestion.docling.processor import DoclingProcessor
from ingestion.chunking.chunker import DocumentChunker
from ingestion.embeddings.bge import BGEEmbeddingModel
from ingestion.classification.qwen_classifier import QwenDocumentClassifier
from retrieval.repositories.document_repository import DocumentRepository


class DocumentIngestionPipeline:
    """
    End-to-end document ingestion pipeline.

    Document
        -> Docling extraction
        -> Qwen3 classification
        -> Chunking
        -> BGE-M3 embeddings
        -> PostgreSQL + pgvector
    """

    def __init__(self):
        self.docling = DoclingProcessor()
        self.classifier = QwenDocumentClassifier()
        self.chunker = DocumentChunker()
        self.embedder = BGEEmbeddingModel()

    def ingest(
        self,
        file_path: str,
        project_id: str,
        category: str | None = None,
        document_type: str | None = None,
    ):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        session = SessionLocal()

        try:
            repository = DocumentRepository(session)

            # 1. Docling extracts machine-readable content
            processed = self.docling.process(path)

            # 2. Classify the document using Qwen3
            classification = self.classifier.classify(
                file_name=path.name,
                document_text=processed["text"],
            )

            # Use AI classification unless explicitly overridden.
            final_category = category or classification.category
            final_document_type = (
                document_type or classification.document_type
            )

            # 3. Create document record
            document = repository.create_document(
                project_id=project_id,
                file_name=path.name,
                storage_key=str(path),
                category=final_category,
                document_type=final_document_type,
            )

            # 4. Split extracted text into chunks
            chunks = self.chunker.chunk(
                document_id=document.id,
                text=processed["text"],
            )

            if not chunks:
                raise ValueError(
                    f"No usable text extracted from {path.name}"
                )

            # 5. Generate BGE-M3 embeddings
            texts = [chunk.content for chunk in chunks]
            embeddings = self.embedder.embed_documents(texts)

            # 6. Store chunks + embeddings
            for chunk, embedding in zip(chunks, embeddings):
                repository.create_chunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    embedding=embedding,
                )

            # 7. Commit everything
            repository.save()

            return {
                "document_id": document.id,
                "file_name": path.name,
                "category": final_category,
                "document_type": final_document_type,
                "classification_confidence": classification.confidence,
                "classification_reasoning": classification.reasoning,
                "classification_signals": classification.signals,
                "chunks": len(chunks),
                "embedding_dimension": self.embedder.dimension,
                "status": "READY",
            }

        finally:
            session.close()
