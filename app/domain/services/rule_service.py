"""Rule service - business logic for categorization rules."""

from typing import Optional

from sqlalchemy.orm import Session

from ...models import USER_ID, Rule
from ...infrastructure.repositories import RuleRepository, CategoryRepository, TransactionRepository
from ...infrastructure.ai import AICategorizer
from ..exceptions import NotFoundError
from ..utils import from_cents, to_cents


class RuleService:
    """Service for rule-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RuleRepository(db)
        self.category_repo = CategoryRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.ai = AICategorizer()

    def get(self, rule_id: int) -> Rule:
        """Get rule by ID or raise NotFoundError."""
        rule = self.repo.get(rule_id)
        if rule is None:
            raise NotFoundError("Rule", rule_id)
        return rule

    def list_all(self) -> list[dict]:
        """List all rules with category info."""
        rules = self.repo.get_all_ordered()
        cats = self.category_repo.get_category_ids_map()

        result = []
        for r in rules:
            cat = cats.get(r.category_id)
            parent = cats.get(cat.parent_id) if cat and cat.parent_id else None

            result.append({
                "id": r.id,
                "pattern": r.pattern,
                "priority": r.priority,
                "category_id": r.category_id,
                "category": f"{parent.name} > {cat.name}" if parent else (cat.name if cat else "Unknown"),
                "min_amount": from_cents(r.min_cents),
                "max_amount": from_cents(r.max_cents),
                "account_id": r.account_id,
            })

        return result

    def create(
        self,
        pattern: str,
        category_id: int,
        priority: int = 100,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        account_id: Optional[int] = None,
    ) -> int:
        """Create a new rule."""
        # Validate category exists
        if self.category_repo.get(category_id) is None:
            raise NotFoundError("Category", category_id)

        rule = Rule(
            user_id=USER_ID,
            pattern=pattern,
            category_id=category_id,
            priority=priority,
            min_cents=None if min_amount is None else to_cents(min_amount),
            max_cents=None if max_amount is None else to_cents(max_amount),
            account_id=account_id,
        )

        self.repo.add(rule)
        self.repo.commit()
        return rule.id

    def delete(self, rule_id: int) -> None:
        """Delete a rule."""
        rule = self.get(rule_id)
        self.repo.delete(rule)
        self.repo.commit()

    def match(
        self,
        text: str,
        amount_cents: Optional[int] = None,
        account_id: Optional[int] = None,
    ) -> Optional[Rule]:
        """Find matching rule for text."""
        return self.repo.match(text, amount_cents, account_id)

    def suggest(
        self,
        text: str,
        amount: Optional[float] = None,
    ) -> dict:
        """Suggest category based on rules."""
        amount_cents = None if amount is None else to_cents(amount)
        rule = self.match(text, amount_cents)

        return {
            "category_id": rule.category_id if rule else None,
            "rule_id": rule.id if rule else None,
        }

    def suggest_pattern(self, description: str) -> Optional[str]:
        """Use AI to suggest a good rule pattern."""
        return self.ai.suggest_rule_pattern(description)

    def apply_to_uncategorized(self) -> int:
        """Apply rules to all uncategorized transactions."""
        transactions = self.transaction_repo.get_uncategorized(["expense", "income"])
        count = 0

        for tx in transactions:
            rule = self.match(
                f"{tx.description} {tx.note}",
                tx.amount_cents,
                tx.account_id,
            )
            if rule:
                tx.category_id = rule.category_id
                count += 1

        self.repo.commit()
        return count
