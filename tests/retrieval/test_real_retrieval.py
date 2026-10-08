from database.session import SessionLocal
from ingestion.embeddings.bge import BGEEmbeddingModel
from retrieval.repositories.document_repository import DocumentRepository


PROJECT_ID = "TEST-PROJECT-001"


def main():
    embedder = BGEEmbeddingModel()
    session = SessionLocal()

    try:
        repository = DocumentRepository(session)

        document = repository.create_document(
            project_id=PROJECT_ID,
            file_name="financial_test.txt",
            storage_key="test/financial_test.txt",
            category="financial",
            document_type="financial_report",
        )

        texts = [
            "The company reported revenue of INR 100 crore for FY 2025-26.",
            "The company reported operating profit of INR 15 crore for FY 2025-26.",
            "The company has outstanding debt of INR 30 crore.",
        ]

        embeddings = embedder.embed_documents(texts)

        for index, (text, embedding) in enumerate(
            zip(texts, embeddings)
        ):
            repository.create_chunk(
                document_id=document.id,
                chunk_index=index,
                content=text,
                embedding=embedding,
            )

        repository.save()

        query = "What was the company's revenue?"

        query_embedding = embedder.embed_query(query)

        results = repository.search_similar_chunks(
            query_embedding=query_embedding,
            limit=3,
            project_id=PROJECT_ID,
        )

        print("RETRIEVAL TEST OK")
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
