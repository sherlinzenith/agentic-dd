from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from storage.document_storage import LocalDocumentStorage
from ingestion.pipeline.document_pipeline import DocumentIngestionPipeline


router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
)

storage = LocalDocumentStorage()
pipeline = DocumentIngestionPipeline()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is required.",
        )

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        storage_key = storage.save(
            file_name=file.filename,
            content=content,
            project_id=project_id,
        )

        result = pipeline.ingest(
            file_path=storage_key,
            project_id=project_id,
        )

        return {
            "success": True,
            "document": result,
            "storage_key": storage_key,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
