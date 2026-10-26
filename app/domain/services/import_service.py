"""Import service - business logic for importing transactions."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ...models import USER_ID, Account, ImportBatch, Transaction
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
        filename: str = "",
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

        # Create import batch for rollback capability
        batch = ImportBatch(
            user_id=USER_ID,
            account_id=account_id,
            filename=filename or "unknown",
            transaction_count=0,
        )
        self.db.add(batch)
        self.db.flush()  # Get the batch ID

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

            # Check for transfer to own account by suffix
            suffix = extract_account_suffix_from_description(tx.description)
            other_account = None

            if suffix and suffix in account_suffixes:
                other_account = self.account_repo.get_by_suffix(suffix)

            # If no suffix match, try pattern-based account matching
            if not other_account:
                other_account = self._match_account_by_pattern(tx.description)

            if other_account and other_account.id != account_id:
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
                    tx, source_account_id, dest_account_id, amount_cents, batch.id
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
                is_business=account.is_business,
                import_hash=tx.import_hash,
                import_batch_id=batch.id,
            )
            self.transaction_repo.add(t)
            imported += 1

        # Update checkpoint and batch count
        if imported > 0 and latest_date:
            account.last_import_at = datetime.now(timezone.utc).replace(tzinfo=None)
            account.last_tx_date = latest_date

        batch.transaction_count = imported

        self.transaction_repo.commit()

        return {
            "imported": imported,
            "skipped": skipped,
            "skipped_checkpoint": skipped_checkpoint,
            "rule_categorized": rule_categorized,
            "ai_categorized": ai_categorized,
            "batch_id": batch.id,
        }

    # Patterns to match account names in transaction descriptions
    ACCOUNT_PATTERNS = [
        (r"APPLECARD|APPLE\s*CARD|GSBANK.*PAYMENT", "Apple Card"),
        (r"AMAZON.*SYNCB|SYNCB.*AMAZON", "Amazon"),
        (r"CHASE\s*CREDIT\s*CRD|CHASE\s*CC", "Chase CC"),
        (r"BOFA\s*CC|BANK\s*OF\s*AMERICA.*CARD", "BOFA CC"),
    ]

    def _match_account_by_pattern(self, description: str) -> Optional[Account]:
        """Try to match an account by description pattern."""
        import re

        for pattern, account_name in self.ACCOUNT_PATTERNS:
            if re.search(pattern, description, re.IGNORECASE):
                return self.account_repo.get_by_name(account_name)
        return None

    def _create_transfer_pair(
        self,
        tx: ParsedTransaction,
        source_account_id: int,
        dest_account_id: int,
        amount_cents: int,
        batch_id: int,
    ) -> None:
        """Create a pair of transfer transactions."""
        # Get account business flags
        source_account = self.account_repo.get(source_account_id)
        dest_account = self.account_repo.get(dest_account_id)
        source_is_business = source_account.is_business if source_account else False
        dest_is_business = dest_account.is_business if dest_account else False

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
            is_business=source_is_business,
            import_hash=tx.import_hash,
            import_batch_id=batch_id,
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
            is_business=dest_is_business,
            import_hash=tx.import_hash + "_in",
            import_batch_id=batch_id,
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

    def get_import_history(self, limit: int = 50) -> list[dict]:
        """Get list of past imports."""
        from sqlalchemy import select

        batches = self.db.scalars(
            select(ImportBatch)
            .where(ImportBatch.user_id == USER_ID)
            .order_by(ImportBatch.imported_at.desc())
            .limit(limit)
        ).all()

        result = []
        for b in batches:
            account = self.account_repo.get(b.account_id)
            result.append({
                "id": b.id,
                "account_id": b.account_id,
                "account_name": account.name if account else "Unknown",
                "filename": b.filename,
                "imported_at": b.imported_at.isoformat(),
                "transaction_count": b.transaction_count,
                "reverted": b.reverted,
            })

        return result

    def revert_import(self, batch_id: int) -> dict:
        """Revert an import by deleting all transactions in the batch."""
        from sqlalchemy import select

        # Get the batch
        batch = self.db.scalars(
            select(ImportBatch).where(
                ImportBatch.id == batch_id,
                ImportBatch.user_id == USER_ID
            )
        ).first()

        if batch is None:
            raise NotFoundError("ImportBatch", batch_id)

        if batch.reverted:
            from ..exceptions import ValidationError
            raise ValidationError("This import has already been reverted")

        # Delete all transactions in this batch
        deleted = self.db.query(Transaction).filter(
            Transaction.import_batch_id == batch_id
        ).delete(synchronize_session=False)

        # Mark batch as reverted
        batch.reverted = True

        self.db.commit()

        return {
            "batch_id": batch_id,
            "deleted_count": deleted,
        }
