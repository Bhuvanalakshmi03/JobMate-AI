"""Resume Intelligence API v1 routes (/api/v1/resumes/*)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.v1.schemas.common import TaskStatusResponse
from app.core.dependencies import DBSessionDep, SettingsDep
from app.integrations.llm.factory import create_llm_client
from app.integrations.openai.client import LLMClientProtocol
from app.integrations.storage.local import LocalPrivateStorage, StorageBackendProtocol
from app.modules.authentication.dependencies import CurrentUserDep
from app.modules.resume.extractor import ResumeAnalystExtractor, ResumeExtractorProtocol
from app.modules.resume.parser import ResumeParser
from app.modules.resume.schemas import (
    ResumeAnalysisResponse,
    ResumeDetailResponse,
    ResumeFactsPatchRequest,
    ResumeFactsPatchResponse,
    ResumeListResponse,
    ResumeSummaryResponse,
)
from app.modules.resume.service import ResumeService
from app.modules.resume.tasks import analyze_resume_task
from app.modules.resume.validator import ResumeExtractionValidator

router = APIRouter(prefix="/resumes", tags=["Resumes"])


def get_storage_backend(settings: SettingsDep) -> StorageBackendProtocol:
    """Provide configured private file storage adapter."""
    return LocalPrivateStorage(settings.local_storage_path)


def get_llm_client(settings: SettingsDep) -> LLMClientProtocol:
    """Provide active LLM chat client (OpenAI or Claude based on LLM_MODE)."""
    return create_llm_client(settings)


def get_resume_extractor(
    llm_client: Annotated[LLMClientProtocol, Depends(get_llm_client)],
) -> ResumeExtractorProtocol:
    """Provide Resume Analyst AI extractor."""
    return ResumeAnalystExtractor(llm_client)


def get_resume_service(
    session: DBSessionDep,
    settings: SettingsDep,
    storage: Annotated[StorageBackendProtocol, Depends(get_storage_backend)],
    extractor: Annotated[ResumeExtractorProtocol, Depends(get_resume_extractor)],
) -> ResumeService:
    """Build request-scoped ResumeService."""
    return ResumeService(
        session=session,
        settings=settings,
        storage=storage,
        parser=ResumeParser(settings),
        extractor=extractor,
        validator=ResumeExtractionValidator(),
    )


ResumeServiceDep = Annotated[ResumeService, Depends(get_resume_service)]


@router.post(
    "/upload",
    response_model=ResumeSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a PDF or DOCX resume",
)
async def upload_resume(
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
    file: Annotated[UploadFile, File(...)],
) -> ResumeSummaryResponse:
    """Validate file signature/size/pages, store privately, and extract text."""
    data = await file.read()
    return await service.upload_resume(
        user=current_user,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )


@router.get(
    "",
    response_model=ResumeListResponse,
    summary="List uploaded resumes for the authenticated user",
)
async def list_resumes(
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ResumeListResponse:
    return await service.list_resumes(user=current_user, limit=limit, offset=offset)


@router.get(
    "/{resume_id}",
    response_model=ResumeDetailResponse,
    summary="Get resume details and parsed text",
)
async def get_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
) -> ResumeDetailResponse:
    return await service.get_resume(user=current_user, resume_id=resume_id)


@router.post(
    "/{resume_id}/analyze",
    response_model=ResumeAnalysisResponse | TaskStatusResponse,
    summary="Analyze resume text and extract verifiable career facts",
)
async def analyze_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
    force: bool = Query(default=False),
    async_mode: bool = Query(default=False),
) -> ResumeAnalysisResponse | TaskStatusResponse:
    if async_mode:
        # Ensure resume belongs to current user before queuing background task
        await service.get_resume(user=current_user, resume_id=resume_id)
        task = analyze_resume_task.delay(str(resume_id), str(current_user.id), force)
        return TaskStatusResponse(
            task_id=str(task.id),
            status="processing",
            message="Resume analysis has started.",
        )
    return await service.analyze_resume(user=current_user, resume_id=resume_id, force=force)


@router.get(
    "/{resume_id}/analysis",
    response_model=ResumeAnalysisResponse,
    summary="Get resume analysis summary and extracted facts",
)
async def get_resume_analysis(
    resume_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
) -> ResumeAnalysisResponse:
    return await service.get_analysis(user=current_user, resume_id=resume_id)


@router.patch(
    "/{resume_id}/facts",
    response_model=ResumeFactsPatchResponse,
    summary="Verify, correct, or reject extracted resume facts and sync profile",
)
async def patch_resume_facts(
    resume_id: uuid.UUID,
    payload: ResumeFactsPatchRequest,
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
) -> ResumeFactsPatchResponse:
    return await service.patch_facts(user=current_user, resume_id=resume_id, payload=payload)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an uploaded resume and its extracted facts",
)
async def delete_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: ResumeServiceDep,
) -> None:
    await service.delete_resume(user=current_user, resume_id=resume_id)
