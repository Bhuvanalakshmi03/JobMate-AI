"""AI Document Generation API v1 routes (/api/v1/documents/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.dependencies import DBSessionDep, SettingsDep
from app.integrations.llm.factory import create_llm_client
from app.integrations.openai.client import LLMClientProtocol
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.documents.generator import DocumentGeneratorProtocol, OpenAIDocumentGenerator
from app.modules.documents.schemas import (
    ApplicationNoteRequest,
    CoverLetterRequest,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    ExportFormat,
    TailorResumeRequest,
)
from app.modules.documents.service import DocumentService
from app.modules.documents.validator import DocumentFactualityValidator

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_llm_client_for_documents(settings: SettingsDep) -> LLMClientProtocol:
    return create_llm_client(settings)


def get_document_generator(
    llm_client: Annotated[LLMClientProtocol, Depends(get_llm_client_for_documents)],
) -> DocumentGeneratorProtocol:
    return OpenAIDocumentGenerator(llm_client)


def get_document_service(
    session: DBSessionDep,
    generator: Annotated[DocumentGeneratorProtocol, Depends(get_document_generator)],
) -> DocumentService:
    return DocumentService(
        session=session,
        generator=generator,
        validator=DocumentFactualityValidator(),
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@router.post(
    "/tailor-resume",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a job-specific tailored resume from verified facts",
)
async def tailor_resume(
    payload: TailorResumeRequest,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    return await service.tailor_resume(user=current_user, payload=payload)


@router.post(
    "/cover-letter",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a job-specific cover letter from verified facts",
)
async def generate_cover_letter(
    payload: CoverLetterRequest,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    return await service.generate_cover_letter(user=current_user, payload=payload)


@router.post(
    "/application-note",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a short job-specific application note",
)
async def generate_application_note(
    payload: ApplicationNoteRequest,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentResponse:
    return await service.generate_application_note(user=current_user, payload=payload)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List generated documents owned by the authenticated user",
)
async def list_documents(
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    job_id: Annotated[uuid.UUID | None, Query()] = None,
    document_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    return await service.list_documents(
        user=current_user,
        job_id=job_id,
        document_type=document_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get a generated document and its version history",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentDetailResponse:
    return await service.get_document(user=current_user, document_id=document_id)


@router.patch(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Edit generated document content and optionally create a new version",
)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentDetailResponse:
    return await service.update_document(
        user=current_user,
        document_id=document_id,
        payload=payload,
    )


@router.get(
    "/{document_id}/download",
    summary="Download generated document as ATS-friendly PDF, DOCX, or Markdown",
)
async def download_document(
    document_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: DocumentServiceDep,
    format: Annotated[ExportFormat, Query()] = "pdf",
) -> Response:
    data, media_type, filename = await service.export_document(
        user=current_user,
        document_id=document_id,
        export_format=format,
    )
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
