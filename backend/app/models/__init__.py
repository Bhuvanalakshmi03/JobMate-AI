"""ORM model registry ensuring Alembic discovers all mapped tables."""

from app.database.base import Base
from app.models.audit_log import AuditLog
from app.modules.agents.models import WorkflowRun
from app.modules.applications.models import Application, ApplicationHistory
from app.modules.approvals.models import ApprovalRequest
from app.modules.authentication.models import OAuthState, User, UserSession
from app.modules.calendar.models import GoogleCalendarConnection
from app.modules.copilot.models import CopilotConversation, CopilotMessage
from app.modules.documents.models import GeneratedDocument
from app.modules.jobs.models import Job, SavedJob
from app.modules.matching.models import JobMatch
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
    "Job",
    "SavedJob",
    "JobMatch",
    "GeneratedDocument",
    "Application",
    "ApplicationHistory",
    "WorkflowRun",
    "ApprovalRequest",
    "GoogleCalendarConnection",
    "CopilotConversation",
    "CopilotMessage",
]
