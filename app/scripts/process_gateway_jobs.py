from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.gateway_job_runner import GatewayJobRunner


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        runner = GatewayJobRunner(db)
        processed = runner.run_due_jobs(limit=settings.async_job_batch_size)
        print(f"processed_jobs={len(processed)}")
        for request_id in processed:
            print(request_id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
