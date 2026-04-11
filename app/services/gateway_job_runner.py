from sqlalchemy.orm import Session

from app.services.gateway_executor import GatewayExecutor


class GatewayJobRunner:
    def __init__(self, db: Session):
        self.db = db
        self.executor = GatewayExecutor(db)

    def run_due_jobs(self, limit: int | None = None) -> list[str]:
        results = self.executor.process_due_requests(limit=limit)
        return [item.request_id for item in results]
