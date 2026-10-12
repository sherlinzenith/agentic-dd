from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from chatbot.models import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    SendMessageRequest,
)
from chatbot.service import ChatbotService

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/chat",
    tags=["chat"],
)

service = ChatbotService()


@router.get("/model-runtime-status")
def get_model_runtime_status(project_id: str):
    """
    Verify the actual loaded model at runtime from the Ollama engine,
    ensuring Llama isolation and confirming model installation.
    """
    try:
        return service.verify_runtime_model()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(project_id: str):
    """List all due diligence conversations for the specified project."""
    try:
        return service.list_conversations(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(project_id: str, request: CreateConversationRequest):
    """Create a new due diligence conversation within the project scope."""
    try:
        return service.create_conversation(project_id, request.title)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(project_id: str, conversation_id: str):
    """Get conversation details and full message history."""
    try:
        conv = service.get_conversation(project_id, conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found or does not belong to this project.")
        return conv
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
def delete_conversation(project_id: str, conversation_id: str):
    """Delete a conversation and all its messages."""
    try:
        deleted = service.delete_conversation(project_id, conversation_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        return {"status": "success", "message": "Conversation deleted."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
def send_message(project_id: str, conversation_id: str, request: SendMessageRequest):
    """
    Ask a due diligence question within a project conversation.
    Retrieves evidence from project documents and findings, invokes Llama,
    and returns an evidence-grounded answer with source citations.
    """
    try:
        return service.ask(
            project_id=project_id,
            conversation_id=conversation_id,
            question=request.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
