"""Category service - business logic for categories."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...models import USER_ID, Category
from ...infrastructure.repositories import (
    CategoryRepository,
    BudgetRepository,
    RuleRepository,
    TransactionRepository,
)
from ..exceptions import CategoryError, DuplicateError, NotFoundError, ValidationError


class CategoryService:
    """Service for category-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.rule_repo = RuleRepository(db)
        self.transaction_repo = TransactionRepository(db)

    def get(self, category_id: int) -> Category:
        """Get category by ID or raise NotFoundError."""
        category = self.repo.get(category_id)
        if category is None:
            raise NotFoundError("Category", category_id)
        return category

    def get_tree(self) -> list[dict]:
        """Get category tree structure."""
        return self.repo.build_tree()

    def get_flat_list_for_ai(self) -> list[dict]:
        """Get flat list of categories for AI."""
        return self.repo.get_flat_list_for_ai()

    def create(
        self,
        name: str,
        parent_id: Optional[int] = None,
        emoji: str = "",
        exclude_from_budget: bool = False,
    ) -> int:
        """Create a new category."""
        # Validate parent if provided
        if parent_id is not None:
            parent = self.get(parent_id)
            if parent.parent_id is not None:
                raise ValidationError("Only two levels are supported (category > subcategory)")

        category = Category(
            user_id=USER_ID,
            name=name,
            parent_id=parent_id,
            emoji=emoji,
            exclude_from_budget=exclude_from_budget,
        )

        self.repo.add(category)
        try:
            self.repo.commit()
        except IntegrityError:
            self.repo.rollback()
            raise DuplicateError("That category already exists under this parent")

        return category.id

    def update(
        self,
        category_id: int,
        name: Optional[str] = None,
        emoji: Optional[str] = None,
        exclude_from_budget: Optional[bool] = None,
    ) -> None:
        """Update a category."""
        category = self.get(category_id)

        if name is not None:
            category.name = name
        if emoji is not None:
            category.emoji = emoji
        if exclude_from_budget is not None:
            category.exclude_from_budget = exclude_from_budget

        self.repo.commit()

    def get_transaction_counts(self, category_id: int) -> dict:
        """Get transaction counts for a category and its subcategories."""
        category = self.get(category_id)
        children = self.repo.get_children(category_id)

        result = []

        # Check parent
        parent_count = self.transaction_repo.count_by_category(category_id)
        if parent_count > 0:
            result.append({"id": category.id, "name": category.name, "count": parent_count})

        # Check children
        for child in children:
            child_count = self.transaction_repo.count_by_category(child.id)
            if child_count > 0:
                result.append({"id": child.id, "name": child.name, "count": child_count})

        total = sum(r["count"] for r in result)
        return {"categories": result, "total": total, "child_count": len(children)}

    def move_transactions(self, from_category_id: int, to_category_id: int) -> int:
        """Move all transactions from one category (and its children) to another."""
        self.get(from_category_id)  # Validate exists
        self.get(to_category_id)  # Validate exists

        source_ids = self.repo.get_category_with_children_ids(from_category_id)
        count = self.transaction_repo.move_to_category(source_ids, to_category_id)
        self.repo.commit()

        return count

    def delete(self, category_id: int) -> None:
        """Delete a category (only if it has no children or transactions)."""
        category = self.get(category_id)
        children = self.repo.get_children(category_id)

        if children:
            # Check if any child has transactions
            child_ids = [child.id for child in children]
            child_tx_count = self.transaction_repo.count_by_categories(child_ids)
            if child_tx_count > 0:
                raise CategoryError(
                    f"Cannot delete: subcategories have {child_tx_count} transactions. Reassign them first."
                )
            raise CategoryError(
                f"Cannot delete category with {len(children)} subcategories. Delete subcategories first."
            )

        # Check if category has transactions
        tx_count = self.transaction_repo.count_by_category(category_id)
        if tx_count > 0:
            raise CategoryError(
                f"Cannot delete category with {tx_count} transactions. Reassign them first."
            )

        # Delete related budgets and rules
        self.budget_repo.delete_by_category(category_id)
        self.rule_repo.delete_by_category(category_id)

        # Delete the category
        self.repo.delete(category)
        self.repo.commit()

    def delete_cascade(self, category_id: int) -> int:
        """Delete a category and all its subcategories (only if none have transactions)."""
        category = self.get(category_id)
        children = self.repo.get_children(category_id)

        # Check if parent or any child has transactions
        all_ids = [category_id] + [child.id for child in children]
        tx_count = self.transaction_repo.count_by_categories(all_ids)

        if tx_count > 0:
            raise CategoryError(
                f"Cannot delete: category or subcategories have {tx_count} transactions. Reassign them first."
            )

        # Delete budgets and rules for all
        for cat_id in all_ids:
            self.budget_repo.delete_by_category(cat_id)
            self.rule_repo.delete_by_category(cat_id)

        # Delete children first, then parent
        for child in children:
            self.repo.delete(child)
        self.repo.delete(category)
        self.repo.commit()

        return len(all_ids)

    def get_excluded_category_ids(self) -> set[int]:
        """Get all category IDs that are excluded from budget."""
        return self.repo.get_excluded_category_ids()

    def is_excluded(self, category_id: Optional[int]) -> bool:
        """Check if a category is excluded from budget."""
        return self.repo.is_excluded(category_id)
