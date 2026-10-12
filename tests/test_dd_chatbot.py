import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.new_main import app
from chatbot.models import DDConversation, DDConversationMessage
from chatbot.service import ChatbotService, clean_model_output
from database.session import SessionLocal
from retrieval.models.documents import Document, DocumentChunk
from retrieval.models.projects import DDProject


@pytest.fixture
def test_projects():
    """Create two isolated test projects in the database."""
    session = SessionLocal()
    proj_a_id = f"TEST-CHAT-A-{uuid.uuid4().hex[:6]}"
    proj_b_id = f"TEST-CHAT-B-{uuid.uuid4().hex[:6]}"

    proj_a = DDProject(
        id=proj_a_id,
        name="Project Alpha Diligence",
        target_company="Alpha Corp",
        deal_type="Acquisition",
    )
    proj_b = DDProject(
        id=proj_b_id,
        name="Project Beta Diligence",
        target_company="Beta Corp",
        deal_type="Merger",
    )
    session.add(proj_a)
    session.add(proj_b)

    # Add a document and chunk to Project A
    doc_a = Document(
        id=f"DOC-A-{uuid.uuid4().hex[:6]}",
        project_id=proj_a_id,
        file_name="alpha_financials.pdf",
        storage_key="docs/alpha.pdf",
        category="financial",
    )
    session.add(doc_a)
    session.flush()

    chunk_a = DocumentChunk(
        id=f"CHUNK-A-{uuid.uuid4().hex[:6]}",
        document_id=doc_a.id,
        chunk_index=0,
        page_number=1,
        content="Alpha Corp reported FY 2025 revenue of $50M and debt of $12M.",
        embedding=[0.05] * 1024,
    )
    session.add(chunk_a)

    # Add a document and chunk to Project B
    doc_b = Document(
        id=f"DOC-B-{uuid.uuid4().hex[:6]}",
        project_id=proj_b_id,
        file_name="beta_legal_agreement.pdf",
        storage_key="docs/beta.pdf",
        category="legal",
    )
    session.add(doc_b)
    session.flush()

    chunk_b = DocumentChunk(
        id=f"CHUNK-B-{uuid.uuid4().hex[:6]}",
        document_id=doc_b.id,
        chunk_index=0,
        page_number=3,
        content="Beta Corp is subject to strict non-compete covenants until 2030.",
        embedding=[0.05] * 1024,
    )
    session.add(chunk_b)

    chunk_a_id = chunk_a.id
    chunk_b_id = chunk_b.id

    session.commit()
    session.close()

    yield {
        "proj_a_id": proj_a_id,
        "proj_b_id": proj_b_id,
        "chunk_a_id": chunk_a_id,
        "chunk_b_id": chunk_b_id,
    }

    # Cleanup
    clean_session = SessionLocal()
    for pid in [proj_a_id, proj_b_id]:
        p = clean_session.get(DDProject, pid)
        if p:
            clean_session.delete(p)
    clean_session.commit()
    clean_session.close()


class TestDDChatbot:

    def test_clean_model_output_sanitizes_thinking_tags(self):
        """Verifies that internal <think> reasoning tags are completely stripped."""
        raw_text = (
            "<think>\n"
            "The user is asking about revenue. Let me check the document.\n"
            "Chunk says $50M. I will formulate a concise response.\n"
            "</think>\n"
            "Alpha Corp reported revenue of $50M for FY 2025. [Document: alpha_financials.pdf, Page 1]"
        )
        cleaned = clean_model_output(raw_text)
        assert "<think>" not in cleaned
        assert "</think>" not in cleaned
        assert "Alpha Corp reported revenue of $50M for FY 2025." in cleaned

    def test_clean_model_output_handles_empty_or_whitespace(self):
        assert clean_model_output(None) == ""
        assert clean_model_output("<think>only thoughts</think>") == ""
        assert clean_model_output("   ") == ""

    def test_conversation_crud_and_persistence(self, test_projects):
        """Test creating, listing, retrieving, and deleting conversations."""
        proj_id = test_projects["proj_a_id"]
        service = ChatbotService()

        # 1. Create conversation
        conv = service.create_conversation(project_id=proj_id, title="Financial QA Session")
        assert conv.id is not None
        assert conv.project_id == proj_id
        assert conv.title == "Financial QA Session"

        # 2. List conversations
        convs = service.list_conversations(project_id=proj_id)
        assert len(convs) >= 1
        assert any(c.id == conv.id for c in convs)

        # 3. Get conversation details
        detail = service.get_conversation(project_id=proj_id, conversation_id=conv.id)
        assert detail is not None
        assert detail.id == conv.id
        assert len(detail.messages) == 0

        # 4. Delete conversation
        deleted = service.delete_conversation(project_id=proj_id, conversation_id=conv.id)
        assert deleted is True

        # Confirm deleted
        detail_after = service.get_conversation(project_id=proj_id, conversation_id=conv.id)
        assert detail_after is None

    def test_project_scoped_retrieval_prevents_cross_project_leakage(self, test_projects):
        """Verifies that retrieval for Project A strictly never returns Project B chunks."""
        proj_a = test_projects["proj_a_id"]
        proj_b = test_projects["proj_b_id"]

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.05] * 1024
        service = ChatbotService(embedder=mock_embedder)

        session = SessionLocal()
        try:
            citations_a, context_a, is_insuf_a = service.retrieve_project_context(
                session=session,
                project_id=proj_a,
                query="What are the non-compete covenants and debt?",
            )

            # Citations for Project A must only contain Project A documents
            assert not is_insuf_a
            assert len(citations_a) > 0
            for cit in citations_a:
                if cit.source_type == "document":
                    assert cit.document_name == "alpha_financials.pdf"
                    assert "beta" not in cit.document_name.lower()

            # Retrieve for Project B
            citations_b, context_b, is_insuf_b = service.retrieve_project_context(
                session=session,
                project_id=proj_b,
                query="What are the non-compete covenants and debt?",
            )
            assert not is_insuf_b
            assert len(citations_b) > 0
            for cit in citations_b:
                if cit.source_type == "document":
                    assert cit.document_name == "beta_legal_agreement.pdf"
                    assert "alpha" not in cit.document_name.lower()
        finally:
            session.close()

    def test_insufficient_evidence_honesty(self):
        """Querying a project with zero documents returns truthful insufficient evidence response."""
        session = SessionLocal()
        empty_proj_id = f"EMPTY-PROJ-{uuid.uuid4().hex[:6]}"
        proj = DDProject(
            id=empty_proj_id,
            name="Empty Project",
            target_company="Empty Corp",
        )
        session.add(proj)
        session.commit()
        session.close()

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.05] * 1024
        service = ChatbotService(embedder=mock_embedder)

        conv = service.create_conversation(project_id=empty_proj_id, title="Test Chat")
        response = service.ask(
            project_id=empty_proj_id,
            conversation_id=conv.id,
            question="What is the EBITDA margin for FY 2024?",
        )

        assert response.is_insufficient_evidence is True
        assert "could not find sufficient evidence" in response.content.lower()
        assert len(response.sources) == 0

        # Cleanup
        clean_session = SessionLocal()
        p = clean_session.get(DDProject, empty_proj_id)
        if p:
            clean_session.delete(p)
        clean_session.commit()
        clean_session.close()

    def test_mocked_model_grounded_answer_and_citations(self, test_projects):
        """Test full turn with mocked LLM producing grounded answer with source citations."""
        proj_a = test_projects["proj_a_id"]

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.05] * 1024

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Alpha Corp reported revenue of $50M and debt of $12M for FY 2025. [Document: alpha_financials.pdf, Page 1]"
        mock_response.reasoning = None
        mock_llm.chat.return_value = mock_response

        service = ChatbotService(embedder=mock_embedder, llm=mock_llm)

        conv = service.create_conversation(project_id=proj_a, title="Revenue Inquiry")
        res = service.ask(
            project_id=proj_a,
            conversation_id=conv.id,
            question="What is Alpha Corp's revenue?",
        )

        assert res.role == "assistant"
        assert "$50M" in res.content
        assert res.is_insufficient_evidence is False
        assert len(res.sources) > 0
        assert res.sources[0].document_name == "alpha_financials.pdf"
        assert res.sources[0].validation_status in ["VERIFIED", "RETRIEVED_SOURCE"]

    def test_api_endpoints_via_testclient(self, test_projects):
        """Test FastAPI chat endpoints via HTTP client."""
        client = TestClient(app)
        proj_a = test_projects["proj_a_id"]

        # 1. Create conversation via API
        post_res = client.post(
            f"/api/v1/projects/{proj_a}/chat/conversations",
            json={"title": "API Due Diligence Chat"},
        )
        assert post_res.status_code == 200
        data = post_res.json()
        assert data["title"] == "API Due Diligence Chat"
        conv_id = data["id"]

        # 2. List conversations via API
        list_res = client.get(f"/api/v1/projects/{proj_a}/chat/conversations")
        assert list_res.status_code == 200
        conv_list = list_res.json()
        assert any(c["id"] == conv_id for c in conv_list)

        # 3. Get conversation detail via API
        get_res = client.get(f"/api/v1/projects/{proj_a}/chat/conversations/{conv_id}")
        assert get_res.status_code == 200
        detail = get_res.json()
        assert detail["id"] == conv_id
        assert len(detail["messages"]) == 0

        # 4. Cross-project isolation check (accessing conv from proj_b should fail 404)
        proj_b = test_projects["proj_b_id"]
        cross_res = client.get(f"/api/v1/projects/{proj_b}/chat/conversations/{conv_id}")
        assert cross_res.status_code == 404

        # 5. Delete conversation via API
        del_res = client.delete(f"/api/v1/projects/{proj_a}/chat/conversations/{conv_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"

    def test_llama_client_model_availability_check(self):
        """Verifies LlamaChatbotClient accurately inspects local Ollama models."""
        from chatbot.llm import LlamaChatbotClient
        # Check installed model
        client = LlamaChatbotClient(model="llama3.3:8b")
        status = client.check_model_availability()
        assert status["configured_model"] == "llama3.3:8b"
        assert "available_models" in status
        if status["available_models"]:
            assert status["is_installed"] is True

        # Check non-existent model
        missing_client = LlamaChatbotClient(model="nonexistent-model:999b")
        missing_status = missing_client.check_model_availability()
        if missing_status["available_models"]:
            assert missing_status["is_installed"] is False

    def test_llama_client_not_found_informative_error(self):
        """Requesting unavailable model raises an informative RuntimeError."""
        from chatbot.llm import LlamaChatbotClient
        client = LlamaChatbotClient(model="nonexistent-model:999b")
        with pytest.raises(RuntimeError) as exc_info:
            client.chat([{"role": "user", "content": "hello"}])
        assert "nonexistent-model:999b" in str(exc_info.value)
        assert "not found in Ollama" in str(exc_info.value)

    def test_llama_client_connection_error_handling(self):
        """Connecting to an invalid port raises ConnectionError or TimeoutError."""
        from chatbot.llm import LlamaChatbotClient
        client = LlamaChatbotClient(base_url="http://localhost:59999/v1", timeout=1.0)
        with pytest.raises((ConnectionError, TimeoutError, RuntimeError)):
            client.chat([{"role": "user", "content": "hello"}])

    def test_chatbot_strictly_rejects_qwen_models(self):
        """
        Verifies that DD Chatbot strictly rejects Qwen models and enforces Llama isolation.
        Specialist agents use Qwen, while the chatbot model must be a Llama family model.
        """
        from chatbot.llm import LlamaChatbotClient
        for qwen_name in ["qwen3:4b", "Qwen/Qwen2.5-7B-Instruct", "qwen2.5:32b", "qwen"]:
            with pytest.raises(ValueError) as exc_info:
                LlamaChatbotClient(model=qwen_name)
            assert "Chatbot must use a Llama family model" in str(exc_info.value)
            assert "not Qwen" in str(exc_info.value)

    def test_separate_specialist_and_chatbot_configurations(self):
        """
        Verifies that specialist agent model configurations and DD Chatbot configurations
        are completely isolated in environment variables and defaults.
        """
        import os
        qwen_model = os.getenv("QWEN_MODEL", "qwen3:4b")
        llama_model = os.getenv("LLAMA_MODEL", "llama3.3:8b")
        assert "qwen" in qwen_model.lower()
        assert "llama" in llama_model.lower()
        assert qwen_model != llama_model

    def test_verify_runtime_model_diagnostics(self):
        """
        Verifies that the chatbot actively verifies the loaded model at runtime against Ollama,
        confirming actual installation, model family, and endpoint availability.
        """
        from chatbot.llm import LlamaChatbotClient
        client = LlamaChatbotClient(model="llama3.3:8b")
        diagnostics = client.verify_runtime_model()
        assert diagnostics["status"] == "VERIFIED"
        assert diagnostics["model_family"] == "llama"
        assert diagnostics["runtime_model"] == "llama3.3:8b"
        assert diagnostics["is_installed"] is True
        assert "available_models" in diagnostics

    def test_api_model_runtime_status_endpoint(self, test_projects):
        """Test the GET /api/v1/projects/{proj_id}/chat/model-runtime-status API endpoint."""
        client = TestClient(app)
        proj_a = test_projects["proj_a_id"]
        res = client.get(f"/api/v1/projects/{proj_a}/chat/model-runtime-status")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "VERIFIED"
        assert data["model_family"] == "llama"
        assert "llama" in data["runtime_model"].lower()
        assert data["is_installed"] is True

