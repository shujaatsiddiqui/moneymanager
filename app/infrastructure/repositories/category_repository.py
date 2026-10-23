"""Category repository."""

from collections import defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import USER_ID, Category
from .base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category entities."""

    def __init__(self, db: Session):
        super().__init__(db, Category)

    def get_all_ordered(self) -> list[Category]:
        """Get all categories ordered by sort and id."""
        return list(self.db.scalars(
            select(Category)
            .where(Category.user_id == self.user_id)
            .order_by(Category.sort, Category.id)
        ).all())

    def get_children(self, parent_id: int) -> list[Category]:
        """Get all children of a category."""
        return list(self.db.scalars(
            select(Category).where(
                Category.user_id == self.user_id,
                Category.parent_id == parent_id
            )
        ).all())

    def get_parent_categories(self) -> list[Category]:
        """Get all parent (top-level) categories."""
        return list(self.db.scalars(
            select(Category).where(
                Category.user_id == self.user_id,
                Category.parent_id.is_(None)
            ).order_by(Category.sort, Category.id)
        ).all())

    def get_children_map(self) -> dict[int, list[Category]]:
        """Get a map of parent_id to list of children."""
        categories = self.get_all_ordered()
        children_map: dict[int, list[Category]] = defaultdict(list)
        for cat in categories:
            if cat.parent_id:
                children_map[cat.parent_id].append(cat)
        return children_map

    def get_category_ids_map(self) -> dict[int, Category]:
        """Get a map of category_id to Category."""
        return {c.id: c for c in self.get_all_ordered()}

    def get_excluded_category_ids(self) -> set[int]:
        """Get all category IDs that are excluded from budget."""
        categories = self.get_all()
        excluded = set()
        parent_excluded = {c.id for c in categories if c.exclude_from_budget and c.parent_id is None}

        for c in categories:
            if c.exclude_from_budget:
                excluded.add(c.id)
            elif c.parent_id in parent_excluded:
                excluded.add(c.id)

        return excluded

    def is_excluded(self, category_id: Optional[int]) -> bool:
        """Check if a category is excluded from budget."""
        if category_id is None:
            return False
        return category_id in self.get_excluded_category_ids()

    def get_category_with_children_ids(self, category_id: int) -> list[int]:
        """Get a category ID and all its children IDs."""
        children = self.get_children(category_id)
        return [category_id] + [c.id for c in children]

    def build_tree(self) -> list[dict]:
        """Build category tree structure for API response."""
        categories = self.get_all_ordered()
        children_map = self.get_children_map()

        return [
            {
                "id": c.id,
                "name": c.name,
                "emoji": c.emoji,
                "exclude_from_budget": c.exclude_from_budget,
                "children": [
                    {"id": k.id, "name": k.name, "parent_id": c.id}
                    for k in children_map.get(c.id, [])
                ],
            }
            for c in categories if c.parent_id is None
        ]

    def get_flat_list_for_ai(self) -> list[dict]:
        """Get flat list of categories with their IDs for AI prompt."""
        categories = self.get_all()
        result = []
        parent_map = {c.id: c.name for c in categories if c.parent_id is None}

        for c in categories:
            if c.parent_id is None:
                result.append({"id": c.id, "name": c.name, "parent": None})
            else:
                parent_name = parent_map.get(c.parent_id, "")
                result.append({"id": c.id, "name": f"{parent_name} > {c.name}", "parent": c.parent_id})

        return result
