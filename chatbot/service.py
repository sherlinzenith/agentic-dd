from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from chatbot.llm import LlamaChatbotClient
from chatbot.models import (
    ConversationDetailResponse,
    ConversationResponse,
    DDConversation,
    DDConversationMessage,
    MessageResponse,
    SourceCitation,
)
from chatbot.prompts import CHATBOT_SYSTEM_PROMPT, INSUFFICIENT_EVIDENCE_MESSAGE
from database.session import SessionLocal
from findings.models import Finding
from findings.repository import FindingRepository
from ingestion.embeddings.bge import BGEEmbeddingModel
from retrieval.models.documents import Document, DocumentChunk
from retrieval.repositories.document_repository import DocumentRepository
from retrieval.repositories.project_repository import ProjectRepository
from services.evidence_validation_service import _best_window_similarity, normalize_quotation

logger = logging.getLogger(__name__)


def clean_model_output(raw_text: str | None) -> str:
    """
    Remove any internal chain-of-thought (<think>...</think>) tags and strip markdown wrappers.
    Ensures internal reasoning is never exposed to the user.
    """
    if not raw_text:
        return ""

    text = str(raw_text)

    # 1. Remove <think>...</think> blocks if present
    if "<think>" in text:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # 2. Strip leftover tag fragments
    text = text.replace("<think>", "").replace("</think>", "").strip()

    return text


class ChatbotService:
    """
    Dedicated Evidence-Grounded Due Diligence Chatbot Service.

    Guarantees:
    - Scoped strictly to the active DD project (zero cross-project leakage).
    - Grounds answers on PostgreSQL document chunks and recorded findings.
    - Uses dedicated Llama model via local Ollama (strictly isolated from specialist agents).
    - Truthfully surfaces insufficient evidence when source documents do not support the query.
    - Persists conversations and messages in PostgreSQL.
    """

    def __init__(
        self,
        embedder: BGEEmbeddingModel | None = None,
        llm: LlamaChatbotClient | None = None,
    ):
        self._embedder = embedder
        self._llm = llm

    @property
    def embedder(self) -> BGEEmbeddingModel:
        if self._embedder is None:
            self._embedder = BGEEmbeddingModel()
        return self._embedder

    @property
    def llm(self) -> LlamaChatbotClient:
        if self._llm is None:
            self._llm = LlamaChatbotClient()
        return self._llm

    def verify_runtime_model(self) -> dict[str, Any]:
        """
        Actively inspects the running Ollama engine at runtime.
        Returns runtime verification diagnostic dict or raises an exception.
        """
        return self.llm.verify_runtime_model()

    # ================================================================
    # CONVERSATION MANAGEMENT
    # ================================================================

    def create_conversation(
        self,
        project_id: str,
        title: str | None = None,
    ) -> ConversationResponse:
        session: Session = SessionLocal()
        try:
            proj_repo = ProjectRepository(session)
            project = proj_repo.get_project(project_id)
            if not project:
                raise ValueError(f"Project '{project_id}' not found.")

            conv_title = title.strip() if title and title.strip() else "New Due Diligence Chat"
            conversation = DDConversation(
                project_id=project_id,
                title=conv_title,
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)

            return ConversationResponse(
                id=conversation.id,
                project_id=conversation.project_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                message_count=0,
            )
        finally:
            session.close()

    def list_conversations(
        self,
        project_id: str,
    ) -> List[ConversationResponse]:
        session: Session = SessionLocal()
        try:
            # Query conversations along with message counts
            statement = (
                select(
                    DDConversation,
                    func.count(DDConversationMessage.id).label("msg_count"),
                )
                .outerjoin(DDConversationMessage, DDConversation.id == DDConversationMessage.conversation_id)
                .where(DDConversation.project_id == project_id)
                .group_by(DDConversation.id)
                .order_by(DDConversation.updated_at.desc())
            )
            results = session.execute(statement).all()

            responses = []
            for conv, count in results:
                responses.append(
                    ConversationResponse(
                        id=conv.id,
                        project_id=conv.project_id,
                        title=conv.title,
                        created_at=conv.created_at,
                        updated_at=conv.updated_at,
                        message_count=count,
                    )
                )
            return responses
        finally:
            session.close()

    def get_conversation(
        self,
        project_id: str,
        conversation_id: str,
    ) -> Optional[ConversationDetailResponse]:
        session: Session = SessionLocal()
        try:
            conversation = session.get(DDConversation, conversation_id)
            if not conversation or conversation.project_id != project_id:
                return None

            messages_stmt = (
                select(DDConversationMessage)
                .where(DDConversationMessage.conversation_id == conversation_id)
                .order_by(DDConversationMessage.created_at.asc())
            )
            msgs = session.scalars(messages_stmt).all()

            msg_responses = []
            for m in msgs:
                sources = [SourceCitation(**s) for s in m.sources]
                msg_responses.append(
                    MessageResponse(
                        id=m.id,
                        conversation_id=m.conversation_id,
                        role=m.role,
                        content=m.content,
                        sources=sources,
                        is_insufficient_evidence=m.is_insufficient_evidence,
                        created_at=m.created_at,
                    )
                )

            return ConversationDetailResponse(
                id=conversation.id,
                project_id=conversation.project_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                messages=msg_responses,
            )
        finally:
            session.close()

    def delete_conversation(
        self,
        project_id: str,
        conversation_id: str,
    ) -> bool:
        session: Session = SessionLocal()
        try:
            conversation = session.get(DDConversation, conversation_id)
            if not conversation or conversation.project_id != project_id:
                return False
            session.delete(conversation)
            session.commit()
            return True
        finally:
            session.close()

    # ================================================================
    # RETRIEVAL & CONTEXT BUILDING
    # ================================================================

    def retrieve_project_context(
        self,
        session: Session,
        project_id: str,
        query: str,
        limit_chunks: int = 5,
        limit_findings: int = 4,
    ) -> Tuple[List[SourceCitation], str, bool]:
        """
        Retrieves relevant document chunks and persisted findings strictly for project_id.
        Returns:
            - citations: List[SourceCitation]
            - context_text: Formatted context string for prompt
            - is_insufficient: True if no relevant project content exists
        """
        citations: List[SourceCitation] = []
        context_parts: List[str] = []

        # 1. Document Chunk Retrieval via pgvector
        query_embedding = self.embedder.embed_query(query)
        doc_repo = DocumentRepository(session)
        matching_chunks = doc_repo.search_similar_chunks(
            query_embedding=query_embedding,
            limit=limit_chunks,
            project_id=project_id,
        )

        for i, chunk in enumerate(matching_chunks, start=1):
            doc_name = chunk.document.file_name if chunk.document else "Unknown Document"
            page_num = chunk.page_number or 1

            snippet = chunk.content.strip()
            if len(snippet) > 450:
                snippet = snippet[:447] + "..."

            citations.append(
                SourceCitation(
                    document_id=chunk.document_id,
                    document_name=doc_name,
                    page_number=page_num,
                    chunk_id=chunk.id,
                    source_type="document",
                    snippet=snippet,
                    validation_status="RETRIEVED_SOURCE",
                )
            )

            context_parts.append(
                f"[Source {i}] Document: {doc_name} | Page: {page_num} | Chunk ID: {chunk.id[:8]}\n"
                f"{chunk.content.strip()}\n"
            )

        # 2. Persisted Finding Retrieval for the project
        finding_repo = FindingRepository(session)
        all_findings = finding_repo.list_for_project(project_id)

        # Simple keyword matching against findings to include directly relevant findings
        relevant_findings = []
        query_terms = set(re.findall(r"\w+", query.lower()))
        for f in all_findings:
            f_text = f"{f.title} {f.issue} {f.why_it_matters or ''} {f.evidence_conclusion or ''}".lower()
            f_terms = set(re.findall(r"\w+", f_text))
            overlap = len(query_terms.intersection(f_terms))
            if overlap > 0 or "finding" in query.lower() or "risk" in query.lower() or "issue" in query.lower():
                relevant_findings.append((overlap, f))

        relevant_findings.sort(key=lambda x: x[0], reverse=True)
        top_findings = [f for _, f in relevant_findings[:limit_findings]]

        if top_findings:
            context_parts.append("\n=== RECORDED DUE DILIGENCE FINDINGS ===")
            for j, f in enumerate(top_findings, start=1):
                citations.append(
                    SourceCitation(
                        finding_id=f.id,
                        document_name=f"Finding: {f.title}",
                        source_type="finding",
                        snippet=f"Issue: {f.issue} | Conclusion: {f.evidence_conclusion or 'N/A'}",
                        validation_status="VERIFIED" if f.status == "VERIFIED" else "RECORDED_FINDING",
                    )
                )
                context_parts.append(
                    f"[Finding {j}] Title: {f.title} | Workstream: {f.workstream} | Severity: {f.risk_severity} | Status: {f.status}\n"
                    f"Issue: {f.issue}\n"
                    f"Why It Matters: {f.why_it_matters or 'N/A'}\n"
                    f"Conclusion: {f.evidence_conclusion or 'N/A'}\n"
                )

        if not matching_chunks and not top_findings:
            return [], "", True

        return citations, "\n".join(context_parts), False

    # ================================================================
    # QUESTION ANSWERING
    # ================================================================

    def ask(
        self,
        project_id: str,
        conversation_id: str,
        question: str,
    ) -> MessageResponse:
        """
        Executes an evidence-grounded question-answering turn within a project conversation.
        """
        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")

        session: Session = SessionLocal()
        try:
            # 1. Validate project and conversation
            proj_repo = ProjectRepository(session)
            project = proj_repo.get_project(project_id)
            if not project:
                raise ValueError(f"Project '{project_id}' not found.")

            conversation = session.get(DDConversation, conversation_id)
            if not conversation or conversation.project_id != project_id:
                raise ValueError(f"Conversation '{conversation_id}' not found in project '{project_id}'.")

            # 2. Record User Message
            user_msg = DDConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=clean_question,
            )
            session.add(user_msg)
            session.flush()

            # Update conversation title if this is the first turn
            if conversation.title == "New Due Diligence Chat":
                new_title = clean_question[:45] + ("..." if len(clean_question) > 45 else "")
                conversation.title = new_title

            # 3. Retrieve Evidence
            citations, context_text, is_insufficient = self.retrieve_project_context(
                session=session,
                project_id=project_id,
                query=clean_question,
            )

            # 4. Handle Insufficient Evidence Honestly
            if is_insufficient or not context_text.strip():
                answer_content = (
                    f"I could not find sufficient evidence in the uploaded documents or findings "
                    f"for project '{project.name}' ({project.target_company}) to answer your question.\n\n"
                    f"Please verify that the relevant Financial or Legal documents have been uploaded and ingested."
                )

                asst_msg = DDConversationMessage(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer_content,
                    sources=[],
                    is_insufficient_evidence=True,
                )
                session.add(asst_msg)
                conversation.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(asst_msg)

                return MessageResponse(
                    id=asst_msg.id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=asst_msg.content,
                    sources=[],
                    is_insufficient_evidence=True,
                    created_at=asst_msg.created_at,
                )

            # 5. Build Bounded Prompt with Context and History
            recent_msgs_stmt = (
                select(DDConversationMessage)
                .where(DDConversationMessage.conversation_id == conversation_id)
                .order_by(DDConversationMessage.created_at.desc())
                .limit(6)
            )
            recent_msgs = list(reversed(session.scalars(recent_msgs_stmt).all()))

            system_instruction = CHATBOT_SYSTEM_PROMPT.format(
                project_name=project.name,
                target_company=project.target_company,
            )

            messages = [{"role": "system", "content": system_instruction}]

            # Conversation history (excluding the current user question which will be appended with context)
            for m in recent_msgs[:-1]:
                clean_c = clean_model_output(m.content)
                messages.append({"role": m.role, "content": clean_c})

            user_prompt = (
                f"DOCUMENT & FINDINGS EVIDENCE:\n"
                f"----------------------------------------\n"
                f"{context_text}\n"
                f"----------------------------------------\n\n"
                f"USER QUESTION: {clean_question}\n\n"
                f"Remember: Answer ONLY from the evidence above. Cite inline as [Document Name, Page X] or [Finding: Title]. "
                f"If the evidence does not provide enough information, explicitly say you cannot find sufficient evidence."
            )
            messages.append({"role": "user", "content": user_prompt})

            # 6. Call Local Model (Llama)
            logger.info("Invoking Llama chatbot (%s) for project '%s'...", self.llm.model, project_id)
            model_response = self.llm.chat(
                messages=messages,
                temperature=0.2,
                max_tokens=1500,
            )

            # 7. Clean and Validate Response Content
            if hasattr(model_response, "content") and isinstance(model_response.content, str):
                raw_content = model_response.content or ""
                raw_reasoning = getattr(model_response, "reasoning", "") or ""
            elif hasattr(model_response, "choices") and model_response.choices:
                msg = model_response.choices[0].message
                raw_content = getattr(msg, "content", "") or ""
                raw_reasoning = getattr(msg, "reasoning", "") or getattr(msg, "reasoning_content", "") or ""
            else:
                raw_content = str(model_response)
                raw_reasoning = ""

            final_content = clean_model_output(raw_content)

            # Fallback if content was empty or only whitespace
            if not final_content:
                if raw_reasoning:
                    logger.warning("Chatbot response had reasoning but empty final content. Synthesizing grounded response.")
                final_content = clean_model_output(raw_reasoning)
                if not final_content:
                    final_content = (
                        "The model did not produce a final response. "
                        "Please check that Ollama is responding properly."
                    )

            # Check if model declared insufficient evidence
            is_model_insufficient = any(
                phrase in final_content.lower()
                for phrase in [
                    "insufficient evidence",
                    "not find sufficient evidence",
                    "no evidence found",
                    "could not find any evidence",
                ]
            )

            # 8. Cross-check cited quotations against chunks
            norm_answer = normalize_quotation(final_content)
            for c in citations:
                if c.source_type == "document" and c.snippet:
                    norm_snippet = normalize_quotation(c.snippet)
                    if norm_snippet in norm_answer or (len(norm_snippet) >= 15 and _best_window_similarity(norm_snippet[:60], norm_answer) >= 0.65):
                        c.validation_status = "VERIFIED"
                    else:
                        c.validation_status = "RETRIEVED_SOURCE"
                elif c.source_type == "finding":
                    c.validation_status = "RECORDED_FINDING"

            # 9. Persist Assistant Message
            asst_msg = DDConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=final_content,
                sources=[c.model_dump() for c in citations],
                is_insufficient_evidence=is_model_insufficient,
            )
            session.add(asst_msg)
            conversation.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(asst_msg)

            return MessageResponse(
                id=asst_msg.id,
                conversation_id=conversation_id,
                role="assistant",
                content=asst_msg.content,
                sources=citations,
                is_insufficient_evidence=is_model_insufficient,
                created_at=asst_msg.created_at,
            )

        finally:
            session.close()
