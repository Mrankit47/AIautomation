"""Generic async repository implementing the repository pattern.

Provides reusable CRUD operations for any SQLAlchemy model.
Concrete repositories can subclass and add domain-specific queries.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository for SQLAlchemy models."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by primary key."""
        return await self._session.get(self._model, entity_id)

    async def get_all(self, *, limit: int = 100, offset: int = 0) -> list[ModelType]:
        """Fetch all records with pagination."""
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[ModelType], int]:
        """Return a page of results and the total count."""
        offset = (page - 1) * per_page

        count_stmt = select(func.count()).select_from(self._model)
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        items_stmt = select(self._model).limit(per_page).offset(offset)
        items_result = await self._session.execute(items_stmt)
        items = list(items_result.scalars().all())

        return items, total

    async def create(self, **kwargs: Any) -> ModelType:
        """Create and persist a new record."""
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(
        self,
        entity_id: uuid.UUID,
        **kwargs: Any,
    ) -> ModelType | None:
        """Update an existing record by primary key."""
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, entity_id: uuid.UUID) -> bool:
        """Delete a record by primary key. Returns True if deleted."""
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True

    async def filter_by(self, **kwargs: Any) -> list[ModelType]:
        """Filter records by column values."""
        stmt = select(self._model).filter_by(**kwargs)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **kwargs: Any) -> int:
        """Count records, optionally filtered by column values."""
        stmt = select(func.count()).select_from(self._model)
        if kwargs:
            stmt = stmt.filter_by(**kwargs)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def exists(self, entity_id: uuid.UUID) -> bool:
        """Check whether a record with the given ID exists."""
        instance = await self.get_by_id(entity_id)
        return instance is not None
