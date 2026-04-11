from sqlalchemy import select
from sqlalchemy.orm import Session


class BaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, model, item_id: int):
        return self.db.get(model, item_id)

    def list_all(self, model):
        return self.db.execute(select(model)).scalars().all()
