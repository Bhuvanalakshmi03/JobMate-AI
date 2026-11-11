"""Business logic for user career profiles, preferences, and skills."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.authentication.models import User
from app.modules.profile.models import UserProfile
from app.modules.profile.repository import ProfileRepository, SkillRepository
from app.modules.profile.schemas import (
    ProfileCreateRequest,
    ProfilePayloadBase,
    ProfileResponse,
    ProfileUpdateRequest,
    SkillsListResponse,
    SkillsUpdateRequest,
    UserSkillResponse,
)
from app.repositories.audit_repository import AuditLogRepository


class ProfileService:
    """Manages user career profile lifecycle and normalized skills."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._profiles = ProfileRepository(session)
        self._skills = SkillRepository(session)
        self._audit = AuditLogRepository(session)

    def _to_profile_response(self, user: User, profile: UserProfile) -> ProfileResponse:
        return ProfileResponse(
            id=profile.id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            timezone=user.timezone,
            headline=profile.headline,
            summary=profile.summary,
            phone=profile.phone,
            location=profile.location,
            university=profile.university,
            degree=profile.degree,
            graduation_year=profile.graduation_year,
            experience_level=profile.experience_level,
            years_of_experience=profile.years_of_experience,
            target_roles=list(profile.target_roles),
            preferred_locations=list(profile.preferred_locations),
            work_mode_preferences=list(profile.work_mode_preferences),
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url,
            portfolio_url=profile.portfolio_url,
            ai_consent_given=profile.ai_consent_given,
            notification_consent=profile.notification_consent,
            profile_verified=profile.profile_verified,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )

    def _extract_profile_fields(self, payload: ProfilePayloadBase) -> dict[str, object]:
        return payload.model_dump(exclude={"full_name", "timezone"})

    async def _sync_user_fields(self, user: User, payload: ProfilePayloadBase) -> None:
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.timezone is not None:
            user.timezone = payload.timezone

    async def get_profile(self, *, user: User) -> ProfileResponse:
        profile = await self._profiles.get_by_user_id(user.id)
        if profile is None:
            raise NotFoundError("Career profile not found.")
        return self._to_profile_response(user, profile)

    async def create_profile(
        self,
        *,
        user: User,
        payload: ProfileCreateRequest,
    ) -> ProfileResponse:
        existing = await self._profiles.get_by_user_id(user.id)
        if existing is not None:
            raise ConflictError("Career profile already exists for this user.")

        await self._sync_user_fields(user, payload)
        profile = await self._profiles.create(
            user_id=user.id,
            fields=self._extract_profile_fields(payload),
        )
        await self._audit.record(
            event_type="profile.created",
            user_id=user.id,
            resource_type="user_profile",
            resource_id=str(profile.id),
        )
        return self._to_profile_response(user, profile)

    async def update_profile(
        self,
        *,
        user: User,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse:
        await self._sync_user_fields(user, payload)
        fields = self._extract_profile_fields(payload)
        existing = await self._profiles.get_by_user_id(user.id)

        if existing is None:
            profile = await self._profiles.create(user_id=user.id, fields=fields)
            event_type = "profile.created"
        else:
            profile = await self._profiles.update(existing, fields=fields)
            event_type = "profile.updated"

        await self._audit.record(
            event_type=event_type,
            user_id=user.id,
            resource_type="user_profile",
            resource_id=str(profile.id),
        )
        return self._to_profile_response(user, profile)

    async def get_skills(self, *, user: User) -> SkillsListResponse:
        skills = await self._skills.list_by_user_id(user.id)
        items = [UserSkillResponse.model_validate(s) for s in skills]
        return SkillsListResponse(skills=items, total=len(items))

    async def replace_skills(
        self,
        *,
        user: User,
        payload: SkillsUpdateRequest,
    ) -> SkillsListResponse:
        deduped: dict[tuple[str, str], dict[str, object]] = {}
        for item in payload.skills:
            normalized = item.name.strip().lower()
            key = (normalized, item.category)
            deduped[key] = {
                "name": item.name.strip(),
                "normalized_name": normalized,
                "category": item.category,
                "proficiency": item.proficiency,
                "years_experience": item.years_experience,
                "is_verified": item.is_verified,
                "source": "manual",
            }

        saved = await self._skills.replace_for_user(
            user_id=user.id,
            items=list(deduped.values()),
        )
        await self._audit.record(
            event_type="profile.skills_updated",
            user_id=user.id,
            resource_type="user_skills",
            details={"skill_count": len(saved)},
        )
        items = [UserSkillResponse.model_validate(s) for s in saved]
        return SkillsListResponse(skills=items, total=len(items))

