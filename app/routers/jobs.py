from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import AutomationJob, JobStatus, Profile
from app.schemas import AutomationJobCreate, AutomationJobRead, AutomationPreview
from app.services.automation import AutomationService

router = APIRouter(prefix="/jobs", tags=["jobs"])
automation_service = AutomationService()


@router.get("", response_model=list[AutomationJobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[AutomationJob]:
    stmt = select(AutomationJob).options(selectinload(AutomationJob.profile)).order_by(AutomationJob.created_at.desc())
    return list(db.scalars(stmt).all())


@router.post("", response_model=AutomationJobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: AutomationJobCreate, db: Session = Depends(get_db)) -> AutomationJob:
    profile = db.get(Profile, payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    job = AutomationJob(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/run", response_model=AutomationJobRead)
def run_job(job_id: int, db: Session = Depends(get_db)) -> AutomationJob:
    stmt = select(AutomationJob).options(
        selectinload(AutomationJob.profile).selectinload(Profile.proxy)
    ).where(AutomationJob.id == job_id)
    job = db.scalar(stmt)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = automation_service.run_job(job)
        job.status = result["status"]
        job.output_url = result.get("output_url")
        job.error_message = result.get("error_message")
        job.metadata_json = result.get("metadata_json")
    except NotImplementedError as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error_message = str(exc)

    db.add(job)
    job.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


@router.get("/preview/{profile_id}", response_model=AutomationPreview)
def preview_profile_automation(profile_id: int, db: Session = Depends(get_db)) -> AutomationPreview:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return automation_service.preview_for_profile(profile)
