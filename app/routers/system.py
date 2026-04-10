from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApiKey, AutomationJob, JobStatus, Profile, Proxy
from app.schemas import DashboardStats


def build_dashboard_stats(db: Session) -> DashboardStats:
    profiles = db.scalar(select(func.count(Profile.id))) or 0
    active_profiles = db.scalar(select(func.count(Profile.id)).where(Profile.is_active.is_(True))) or 0
    proxies = db.scalar(select(func.count(Proxy.id))) or 0
    active_api_keys = db.scalar(select(func.count(ApiKey.id)).where(ApiKey.is_active.is_(True))) or 0
    queued_jobs = db.scalar(select(func.count(AutomationJob.id)).where(AutomationJob.status == JobStatus.QUEUED)) or 0
    running_jobs = db.scalar(select(func.count(AutomationJob.id)).where(AutomationJob.status == JobStatus.RUNNING)) or 0
    return DashboardStats(
        profiles=profiles,
        active_profiles=active_profiles,
        proxies=proxies,
        active_api_keys=active_api_keys,
        queued_jobs=queued_jobs,
        running_jobs=running_jobs,
    )
