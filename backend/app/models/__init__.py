"""ORM model registry ensuring Alembic discovers all mapped tables."""

from app.database.base import Base
from app.models.audit_log import AuditLog
from app.modules.authentication.models import OAuthState, User, UserSession
from app.modules.profile.models import UserProfile, UserSkill
from app.modules.resume.models import Resume, ResumeFact

__all__ = [
    "Base",
    "AuditLog",
    "User",
    "UserSession",
    "OAuthState",
    "UserProfile",
    "UserSkill",
    "Resume",
    "ResumeFact",
]
