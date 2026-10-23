"""Import service - business logic for importing transactions."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ...models import USER_ID, Transaction
from ...infrastructure.repositories import AccountRepository, TransactionRepository, RuleRepository
from ...infrastructure.parsers import parse_statement, ParsedTransaction
from ...infrastructure.parsers.statement_parser import extract_account_suffix_from_description
from ...infrastructure.ai import AICategorizer
from ..exceptions import NotFoundError
from ..utils import to_cents


class ImportService:
    """Service for importing transactions from bank statements."""

    def __init__(self, db: Session):
        self.db = db
        self.account_repo = AccountRepository(db)
        self.transaction_repo = TransactionRepository(db)
        self.rule_repo = RuleRepository(db)
        self.ai = AICategorizer()

    def parse_file(self, content: bytes, filename: str) -> tuple[list[ParsedTransaction], str]:
        """Parse a statement file."""
        return parse_statement(content, filename)

    def detect_account(self, content: str, filename: str) -> tuple[Optional[int], Optional[str]]:
        """Detect account from file content/filename.

        Returns:
            Tuple of (account_id, account_name) or (None, None)
        """
        from .account_service import AccountService

        service = AccountService(self.db)
        account_id = service.detect_from_content(content, filename)

        if account_id:
            account = self.account_repo.get(account_id)
            return account_id, account.name if account else None

        return None, None

    def import_transactions(
        self,
        transactions: list[ParsedTransaction],
        account_id: int,
        use_ai: bool = False,
        categories: Optional[list[dict]] = None,
    ) -> dict:
        """Import parsed transactions into the database."""
        imported = 0
        skipped = 0
        skipped_checkpoint = 0
        ai_categorized = 0
        rule_categorized = 0

        # Get account and its checkpoint
        account = self.account_repo.get(account_id)
        if account is None:
            raise NotFoundError("Account", account_id)

        checkpoint = account.last_tx_date

        # Get existing import hashes
        existing_hashes = self.transaction_repo.get_existing_hashes()
        batch_hashes: set[str] = set()

        # Get account suffixes for transfer detection
        account_suffixes = self.account_repo.get_all_suffixes()

        # Get categories for AI if needed
        if use_ai and categories is None:
            from ...infrastructure.repositories import CategoryRepository
            cat_repo = CategoryRepository(self.db)
            categories = cat_repo.get_flat_list_for_ai()

        # Track latest date for checkpoint
        latest_date = None

        for tx in transactions:
            # Skip transactions before checkpoint
            if checkpoint and tx.date < checkpoint:
                skipped_checkpoint += 1
                continue

            # Track latest date
            if latest_date is None or tx.date > latest_date:
                latest_date = tx.date

            # Skip duplicates
            if tx.import_hash in existing_hashes or tx.import_hash in batch_hashes:
                skipped += 1
                continue

            batch_hashes.add(tx.import_hash)

            # Check for transfer to own account
            suffix = extract_account_suffix_from_description(tx.description)
            if suffix and suffix in account_suffixes:
                other_account = self.account_repo.get_by_suffix(suffix)
                if other_account:
                    # Determine source and destination
                    if tx.is_inflow:
                        source_account_id = other_account.id
                        dest_account_id = account_id
                    else:
                        source_account_id = account_id
                        dest_account_id = other_account.id

                    # Check for existing transfer
                    amount_cents = to_cents(tx.amount)
                    existing = self.transaction_repo.find_existing_transfer(
                        tx.date, amount_cents, source_account_id, dest_account_id
                    )
                    if existing:
                        skipped += 1
                        continue

                    # Create transfer pair
                    self._create_transfer_pair(
                        tx, source_account_id, dest_account_id, amount_cents
                    )
                    imported += 2
                    continue

            # Regular transaction (expense or income)
            amount_cents = to_cents(tx.amount)
            category_id = None

            # Try rule-based categorization
            rule = self.rule_repo.match(tx.description, amount_cents, account_id)
            if rule:
                category_id = rule.category_id
                rule_categorized += 1
            elif use_ai and tx.kind == "expense" and categories:
                # Try AI categorization for expenses
                ai_cat_id = self.ai.categorize_single(tx.description, categories)
                if ai_cat_id:
                    category_id = ai_cat_id
                    ai_categorized += 1

            t = Transaction(
                user_id=USER_ID,
                date=tx.date,
                kind=tx.kind,
                amount_cents=amount_cents,
                account_id=account_id,
                to_account_id=None,
                category_id=category_id,
                description=tx.description[:500],
                note="",
                is_business=False,
                import_hash=tx.import_hash,
            )
            self.transaction_repo.add(t)
            imported += 1

        # Update checkpoint
        if imported > 0 and latest_date:
            account.last_import_at = datetime.now(timezone.utc).replace(tzinfo=None)
            account.last_tx_date = latest_date

        self.transaction_repo.commit()

        return {
            "imported": imported,
            "skipped": skipped,
            "skipped_checkpoint": skipped_checkpoint,
            "rule_categorized": rule_categorized,
            "ai_categorized": ai_categorized,
        }

    def _create_transfer_pair(
        self,
        tx: ParsedTransaction,
        source_account_id: int,
        dest_account_id: int,
        amount_cents: int,
    ) -> None:
        """Create a pair of transfer transactions."""
        # transfer_out: deducts from source
        t_out = Transaction(
            user_id=USER_ID,
            date=tx.date,
            kind="transfer_out",
            amount_cents=amount_cents,
            account_id=source_account_id,
            to_account_id=dest_account_id,
            category_id=None,
            description=tx.description[:500],
            note="",
            is_business=False,
            import_hash=tx.import_hash,
        )
        self.transaction_repo.add(t_out)

        # transfer_in: adds to destination
        t_in = Transaction(
            user_id=USER_ID,
            date=tx.date,
            kind="transfer_in",
            amount_cents=amount_cents,
            account_id=dest_account_id,
            to_account_id=source_account_id,
            category_id=None,
            description=tx.description[:500],
            note="",
            is_business=False,
            import_hash=tx.import_hash + "_in",
        )
        self.transaction_repo.add(t_in)

    def check_ai_available(self) -> dict:
        """Check if AI categorization is available."""
        return {
            "available": self.ai.is_available(),
            "model": self.ai.model,
        }

    def preview(self, content: bytes, filename: str) -> dict:
        """Preview transactions from a file without importing."""
        transactions, bank_format = self.parse_file(content, filename)

        # Try to detect account
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        account_id, account_name = self.detect_account(text, filename)

        return {
            "filename": filename,
            "format": bank_format,
            "count": len(transactions),
            "detected_account_id": account_id,
            "detected_account_name": account_name,
            "transactions": [
                {
                    "date": tx.date.isoformat(),
                    "description": tx.description,
                    "amount": tx.amount,
                    "kind": tx.kind,
                }
                for tx in transactions[:50]  # Preview first 50
            ],
        }
