from ingestion.pipeline.document_pipeline import DocumentIngestionPipeline
from database.session import SessionLocal
from retrieval.repositories.document_repository import DocumentRepository
from ingestion.embeddings.bge import BGEEmbeddingModel


PROJECT_ID = "REAL-INGESTION-TEST"


def main():
    file_path = "documents/01_income_statement.pdf"

    pipeline = DocumentIngestionPipeline()

    result = pipeline.ingest(
        file_path=file_path,
        project_id=PROJECT_ID,
        category="financial",
        document_type="income_statement",
    )

    print("DOCUMENT INGESTION OK")
    print(f"DOCUMENT ID: {result['document_id']}")
    print(f"FILE: {result['file_name']}")
    print(f"CATEGORY: {result['category']}")
    print(f"TYPE: {result['document_type']}")
    print(f"CHUNKS: {result['chunks']}")
    print(f"EMBEDDING DIMENSION: {result['embedding_dimension']}")
    print(f"STATUS: {result['status']}")

    # Verify retrieval against the newly ingested document
    embedder = BGEEmbeddingModel()
    session = SessionLocal()

    try:
        repository = DocumentRepository(session)

        query = "What was the company's revenue?"

        query_embedding = embedder.embed_query(query)

        results = repository.search_similar_chunks(
            query_embedding=query_embedding,
            limit=3,
            project_id=PROJECT_ID,
        )

        print()
        print("RETRIEVAL VERIFICATION")
        print(f"QUERY: {query}")
        print(f"RESULTS: {len(results)}")

        for result in results:
            print(
                f"{result.chunk_index}: "
                f"{result.content}"
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()
