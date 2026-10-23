"""Base repository with common CRUD operations."""

from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database import Base
from ...models import USER_ID

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository providing common CRUD operations."""

    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model
        self.user_id = USER_ID

    def get(self, id_: int) -> Optional[T]:
        """Get entity by ID, filtered by user_id."""
        entity = self.db.get(self.model, id_)
        if entity is None or getattr(entity, "user_id", self.user_id) != self.user_id:
            return None
        return entity

    def get_all(self) -> list[T]:
        """Get all entities for current user."""
        return list(self.db.scalars(
            select(self.model).where(self.model.user_id == self.user_id)
        ).all())

    def add(self, entity: T) -> T:
        """Add a new entity."""
        self.db.add(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Delete an entity."""
        self.db.delete(entity)

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()

    def refresh(self, entity: T) -> None:
        """Refresh an entity from the database."""
        self.db.refresh(entity)
