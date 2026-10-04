from typing import List

from models.gateway import get_backend

from .models import QAAnswer, RetrievedChunk
from .retriever import WorkspaceRetriever


# ================================================================
# SYSTEM PROMPT
# ================================================================

SYSTEM_PROMPT = """
You are an AI Due Diligence document assistant.

Your ONLY job is to answer questions using the document
evidence supplied to you.

You are NOT a general knowledge assistant.

============================================================
MOST IMPORTANT RULE
============================================================

Answer ONLY what the supplied documents actually say.

Do NOT answer what a document type generally means.

Do NOT use outside knowledge.

Do NOT invent facts.

Do NOT guess.

Do NOT make assumptions.

Do NOT create information that is not in the evidence.

============================================================
DOCUMENT CONTENT
============================================================

Different documents have different structures.

Do NOT force every document into the same checklist.

Only report information actually present in the evidence.

============================================================
SAMPLE / FICTIONAL / ILLUSTRATIVE
============================================================

If the source says:

SAMPLE

NOT A LEGAL DOCUMENT

FICTIONAL

ILLUSTRATIVE

DEMO

DRAFT

NON-BINDING

preserve that wording when relevant.

Do not turn sample information into real-world facts.

============================================================
NUMBERS
============================================================

Preserve numbers exactly as written.

Do not change:

- amounts
- dates
- percentages
- valuations
- quantities
- periods
- identifiers

============================================================
NO INVENTED MISSING FIELDS
============================================================

Do NOT create statements such as:

"Investor: None specified"

"Valuation: Not provided"

"Rights: No rights defined"

"Risks: No risks discussed"

unless the document explicitly supports that statement.

If something is not relevant or not present,
simply do not mention it.

============================================================
CITATIONS
============================================================

Every factual statement should have:

[Document Name, Page X]

Use the exact document name and page number
provided in the evidence.

============================================================
SUMMARIZATION
============================================================

When the user asks:

"Explain this document"

"Summarize this document"

"What's in this document?"

"What does this document contain?"

summarize the actual document evidence.

Do not reproduce the entire document.

Use concise bullet points.

============================================================
SPECIFIC QUESTIONS
============================================================

If the user asks a specific question,
answer only that question using the evidence.

============================================================
MULTIPLE DOCUMENTS
============================================================

If multiple documents are relevant:

- clearly distinguish them
- cite each document
- do not merge facts
- do not assume information from one document applies
  to another document

============================================================
INSUFFICIENT EVIDENCE
============================================================

If the evidence does not contain enough information,
say:

"I could not find sufficient evidence in the current workspace documents."

Do not use outside knowledge to complete the answer.
"""


# ================================================================
# SETTINGS
# ================================================================

MIN_RELEVANCE_SCORE = 0.20

MAX_EVIDENCE_SOURCES = 3


class DDQAService:
    """
    AI Due Diligence Q&A service.

    Flow:

        User question
             ↓
        Intent detection
             ↓
        Document inventory OR
        RAG retrieval
             ↓
        Evidence filtering
             ↓
        Qwen
             ↓
        Grounded answer
    """

    def __init__(self):

        self.retriever = WorkspaceRetriever()

        # Keep the original documents so that questions such as:
        #
        # "what docs do we have?"
        #
        # can be answered directly without RAG.
        self.documents = []

    # ============================================================
    # BUILD INDEX
    # ============================================================

    def build_index(self, documents):
        """
        Build the FAISS index.

        Also remember the workspace document inventory.
        """

        self.documents = documents or []

        self.retriever.build(
            self.documents
        )

    # ============================================================
    # DOCUMENT INVENTORY INTENT
    # ============================================================

    def _is_document_inventory_question(
        self,
        question: str,
    ) -> bool:
        """
        Detect questions asking which documents exist
        in the current workspace.

        Examples:

        - what docs do we have
        - what documents are available
        - what pdfs do we have
        - list the documents
        - show me the uploaded files
        - what files are in the workspace
        """

        question = (
            question or ""
        ).lower().strip()

        inventory_phrases = [
            "what docs do we have",
            "what documents do we have",
            "what documents are available",
            "what docs are available",
            "what pdfs do we have",
            "what pdf do we have",
            "what files do we have",
            "what files are available",
            "what documents are in the workspace",
            "what docs are in the workspace",
            "what files are in the workspace",
            "list the documents",
            "list documents",
            "list the docs",
            "list docs",
            "list the files",
            "list files",
            "show the documents",
            "show documents",
            "show the docs",
            "show docs",
            "show the files",
            "show files",
            "uploaded documents",
            "uploaded docs",
            "uploaded files",
            "available documents",
            "available docs",
            "available files",
        ]

        for phrase in inventory_phrases:

            if phrase in question:
                return True

        # --------------------------------------------------------
        # More flexible detection for short questions such as:
        #
        # "what docs / pdf do we have"
        #
        # --------------------------------------------------------

        has_what = (
            "what" in question
            or "which" in question
        )

        has_document_word = any(
            word in question
            for word in [
                "doc",
                "docs",
                "document",
                "documents",
                "pdf",
                "pdfs",
                "file",
                "files",
            ]
        )

        has_inventory_word = any(
            phrase in question
            for phrase in [
                "do we have",
                "are available",
                "available",
                "uploaded",
                "in the workspace",
            ]
        )

        return (
            has_what
            and has_document_word
            and has_inventory_word
        )

    # ============================================================
    # DOCUMENT INVENTORY ANSWER
    # ============================================================

    def _document_inventory_answer(
        self,
    ) -> QAAnswer:
        """
        Return the actual workspace document list.

        No LLM is used here.
        No RAG is used here.

        This prevents the AI from inventing relationships
        between documents.
        """

        if not self.documents:

            return QAAnswer(
                answer=(
                    "There are no documents in the "
                    "current workspace."
                ),
                sources=[],
            )

        lines = [
            "The current workspace contains "
            f"{len(self.documents)} document(s):",
            "",
        ]

        for index, document in enumerate(
            self.documents,
            start=1,
        ):

            name = document.get(
                "document",
                "Unknown document",
            )

            lines.append(
                f"{index}. {name}"
            )

        return QAAnswer(
            answer="\n".join(lines),
            sources=[],
        )

    # ============================================================
    # SEARCH
    # ============================================================

    def search(
        self,
        question,
        top_k=5,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant document evidence.
        """

        results = self.retriever.search(
            question,
            top_k=top_k,
        )

        # --------------------------------------------------------
        # Remove weak evidence
        # --------------------------------------------------------

        results = [
            result
            for result in results
            if result.score >= MIN_RELEVANCE_SCORE
        ]

        if not results:
            return []

        # --------------------------------------------------------
        # Strongest evidence first
        # --------------------------------------------------------

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        # --------------------------------------------------------
        # Focus on strongest document
        # --------------------------------------------------------

        results = self._focus_document(
            results
        )

        # --------------------------------------------------------
        # Limit evidence
        # --------------------------------------------------------

        return results[
            :MAX_EVIDENCE_SOURCES
        ]

    # ============================================================
    # DOCUMENT FOCUS
    # ============================================================

    def _focus_document(
        self,
        results: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        If one document is clearly more relevant than
        the others, focus the evidence on that document.
        """

        if not results:
            return []

        strongest = results[0]

        strongest_document = (
            strongest.document
        )

        strongest_score = (
            strongest.score
        )

        same_document = [
            result
            for result in results
            if result.document
            == strongest_document
        ]

        other_results = [
            result
            for result in results
            if result.document
            != strongest_document
        ]

        if other_results:

            second_score = (
                other_results[0].score
            )

            # ----------------------------------------------------
            # Strong document lead
            # ----------------------------------------------------

            if (
                strongest_score
                - second_score
                >= 0.10
            ):
                return same_document

        return results

    # ============================================================
    # ANSWER
    # ============================================================

    def answer(
        self,
        question,
        top_k=5,
    ) -> QAAnswer:
        """
        Answer a Due Diligence question.

        First determine whether the question is asking
        about the workspace document inventory.

        If yes:

            Return documents directly.

        Otherwise:

            Use RAG + Qwen.
        """

        question = (
            question or ""
        ).strip()

        # --------------------------------------------------------
        # Empty question
        # --------------------------------------------------------

        if not question:

            return QAAnswer(
                answer="Please enter a question.",
                sources=[],
            )

        # --------------------------------------------------------
        # DOCUMENT INVENTORY
        # --------------------------------------------------------

        if self._is_document_inventory_question(
            question
        ):

            return self._document_inventory_answer()

        # --------------------------------------------------------
        # RAG
        # --------------------------------------------------------

        sources = self.search(
            question,
            top_k=top_k,
        )

        # --------------------------------------------------------
        # No evidence
        # --------------------------------------------------------

        if not sources:

            return QAAnswer(
                answer=(
                    "I could not find sufficient evidence "
                    "in the current workspace documents."
                ),
                sources=[],
            )

        # --------------------------------------------------------
        # Build evidence blocks
        # --------------------------------------------------------

        evidence_blocks = []

        for index, source in enumerate(
            sources,
            start=1,
        ):

            evidence_blocks.append(
                f"""
============================================================
SOURCE {index}
============================================================

DOCUMENT:
{source.document}

PAGE:
{source.page}

RELEVANCE SCORE:
{source.score:.3f}

DOCUMENT EVIDENCE:
{source.text}
"""
            )

        evidence_text = "\n".join(
            evidence_blocks
        )

        # --------------------------------------------------------
        # LLM prompt
        # --------------------------------------------------------

        prompt = f"""
USER QUESTION
============================================================

{question}


DOCUMENT EVIDENCE
============================================================

{evidence_text}


INSTRUCTIONS
============================================================

Answer the USER QUESTION using ONLY the DOCUMENT EVIDENCE.

Do not use general knowledge.

Do not provide a generic definition of the document type.

Describe the actual information contained in the supplied
document evidence.


IMPORTANT:

Do NOT create a fixed checklist.

Do NOT create fields such as:

- Company
- Investor
- Instrument
- Investment Amount
- Valuation
- Rights
- Obligations
- Risks
- Findings
- Conclusions

unless those items actually appear in the evidence.

If something is not present,
do not mention it.


IF THE USER ASKS TO EXPLAIN OR SUMMARIZE THE DOCUMENT
============================================================

Give a concise summary of the actual contents.

Identify important facts, sections, terms, parties,
dates, clauses, amounts, obligations, rights, findings,
or other information that actually appears.

Only include information supported by the evidence.


DO NOT COPY THE DOCUMENT
============================================================

Summarize the evidence.

Do not reproduce the entire document.

Do not copy large paragraphs.

Use concise bullet points.


SAMPLE / FICTIONAL / ILLUSTRATIVE
============================================================

If the evidence contains:

SAMPLE

NOT A LEGAL DOCUMENT

FICTIONAL

ILLUSTRATIVE

DEMO

DRAFT

NON-BINDING

preserve that wording when relevant.


CITATIONS
============================================================

Every factual bullet should contain:

[Document Name, Page X]

Use the exact document name and page number
provided in the evidence.


NUMBERS
============================================================

Preserve numbers exactly as written.

Do not modify dates, amounts, percentages,
valuations, quantities, or periods.


DO NOT INVENT
============================================================

Do not create statements such as:

"Investor: None specified"

"Valuation: Not provided"

"Rights: No rights defined"

"Risks: No risks discussed"

unless the evidence explicitly supports those statements.


INSUFFICIENT EVIDENCE
============================================================

If the evidence does not contain enough information
to answer the question, say:

I could not find sufficient evidence in the current workspace documents.


FINAL ANSWER
============================================================
"""

        # --------------------------------------------------------
        # Generate answer
        # --------------------------------------------------------

        backend = get_backend()

        answer = backend.generate(
            SYSTEM_PROMPT,
            prompt,
            max_new_tokens=500,
        )

        answer = (
            answer or ""
        ).strip()

        # --------------------------------------------------------
        # Model failure fallback
        # --------------------------------------------------------

        if not answer or len(answer) < 20:

            answer = (
                "The retrieved evidence is from:\n\n"
                + "\n".join(
                    f"- {source.document}, "
                    f"Page {source.page}"
                    for source in sources
                )
                + "\n\n"
                "The AI model did not generate "
                "a complete answer."
            )

        return QAAnswer(
            answer=answer,
            sources=sources,
        )