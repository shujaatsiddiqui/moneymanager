"""Rule repository."""

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import USER_ID, Rule
from .base import BaseRepository


class RuleRepository(BaseRepository[Rule]):
    """Repository for Rule entities."""

    def __init__(self, db: Session):
        super().__init__(db, Rule)

    def get_all_ordered(self) -> list[Rule]:
        """Get all rules ordered by priority and id."""
        return list(self.db.scalars(
            select(Rule)
            .where(Rule.user_id == self.user_id)
            .order_by(Rule.priority, Rule.id)
        ).all())

    def delete_by_category(self, category_id: int) -> int:
        """Delete all rules for a category."""
        count = 0
        for r in self.db.scalars(
            select(Rule).where(Rule.category_id == category_id)
        ):
            self.db.delete(r)
            count += 1
        return count

    def match(
        self,
        text: str,
        amount_cents: Optional[int] = None,
        account_id: Optional[int] = None
    ) -> Optional[Rule]:
        """Find the first matching rule for the given text and optional filters."""
        if not text.strip():
            return None

        for rule in self.get_all_ordered():
            if self._matches_rule(rule, text, amount_cents, account_id):
                return rule
        return None

    def _matches_rule(
        self,
        rule: Rule,
        text: str,
        amount_cents: Optional[int],
        account_id: Optional[int]
    ) -> bool:
        """Check if a rule matches the given criteria."""
        # Account filter
        if rule.account_id is not None and rule.account_id != account_id:
            return False

        # Amount range filter
        if amount_cents is not None:
            if rule.min_cents is not None and amount_cents < rule.min_cents:
                return False
            if rule.max_cents is not None and amount_cents > rule.max_cents:
                return False

        # Pattern matching
        if rule.pattern.lower().startswith("re:"):
            try:
                return re.search(rule.pattern[3:], text, re.IGNORECASE) is not None
            except re.error:
                return False

        return rule.pattern.lower() in text.lower()
