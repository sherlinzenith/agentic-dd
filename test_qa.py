from processing.document_processor import extract_all_documents
from qa.qa_service import DDQAService


DOCUMENTS_DIR = "documents"


def main():

    print("\n==============================")
    print("AI DD Q&A TEST")
    print("==============================")

    print("\n[1] Loading documents...")

    documents = extract_all_documents(
        DOCUMENTS_DIR
    )

    print(
        f"Loaded {len(documents)} document(s)."
    )

    for document in documents:

        print(
            f" - {document['document']}"
        )

    print("\n[2] Building RAG index...")

    qa = DDQAService()

    qa.build_index(
        documents
    )

    print("\n[3] Asking question...")

    question = input(
        "\nAsk a DD question: "
    ).strip()

    if not question:

        print("No question entered.")

        return

    result = qa.answer(
        question
    )

    print("\n==============================")
    print("ANSWER")
    print("==============================")

    print(result.answer)

    print("\n==============================")
    print("SOURCES")
    print("==============================")

    for source in result.sources:

        print(
            f"\n{source.document}"
            f" | Page {source.page}"
            f" | Score {source.score:.3f}"
        )

        print(source.text[:500])


if __name__ == "__main__":
    main()