from pathlib import Path

SUPPORTED = {".txt", ".pdf"}


def extract_text_file(file_path: str):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    return path.read_text(encoding="utf-8-sig")


def extract_pdf_pages(file_path: str):
    """Return a list of page texts (page 1 = index 0)."""
    import fitz  # PyMuPDF

    with fitz.open(file_path) as pdf:
        return [page.get_text() for page in pdf]


def extract_document(file_path: str):
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(str(path))
    else:
        # a form feed (\f) marks a page break in text files
        pages = extract_text_file(str(path)).split("\f")

    return {
        "document": path.name,
        "text": "\n".join(pages),
        "pages": pages,
    }


def extract_all_documents(documents_dir: str):
    directory = Path(documents_dir)

    if not directory.exists():
        raise FileNotFoundError(
            f"Documents directory not found: {documents_dir}"
        )

    files = sorted(
        f for f in directory.iterdir()
        if f.is_file()
        and not f.name.startswith(".")
        and f.suffix.lower() in SUPPORTED
    )

    if not files:
        raise FileNotFoundError(
            f"No supported documents (TXT/PDF) in {documents_dir}"
        )

    return [extract_document(str(f)) for f in files]