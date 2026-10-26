"""Import schemas."""

from typing import Optional

from pydantic import BaseModel


class AIStatusOut(BaseModel):
    """Response schema for AI status."""
    available: bool
    model: str


class ImportResultOut(BaseModel):
    """Response schema for a single file import result."""
    filename: str
    format: Optional[str] = None
    total_in_file: Optional[int] = None
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    auto_detected: bool = False
    imported: int = 0
    skipped: int = 0
    skipped_checkpoint: int = 0
    rule_categorized: int = 0
    ai_categorized: int = 0
    batch_id: Optional[int] = None
    error: Optional[str] = None


class MultiImportOut(BaseModel):
    """Response schema for multi-file import."""
    files: list[ImportResultOut]
    total_imported: int


class PreviewTransactionOut(BaseModel):
    """Preview of a parsed transaction."""
    date: str
    description: str
    amount: float
    kind: str


class PreviewOut(BaseModel):
    """Response schema for import preview."""
    filename: str
    format: str
    count: int
    detected_account_id: Optional[int]
    detected_account_name: Optional[str]
    transactions: list[PreviewTransactionOut]


class ImportHistoryItem(BaseModel):
    """A single import batch in history."""
    id: int
    account_id: int
    account_name: str
    filename: str
    imported_at: str
    transaction_count: int
    reverted: bool


class RevertImportOut(BaseModel):
    """Response schema for reverting an import."""
    batch_id: int
    deleted_count: int
