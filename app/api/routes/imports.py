"""Import routes."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..dependencies import get_import_service, get_account_service, handle_domain_exception
from ..schemas import AIStatusOut, PreviewOut
from ...domain.exceptions import DomainException
from ...domain.services import ImportService, AccountService

router = APIRouter(prefix="/import", tags=["import"])


@router.get("/ai-status", response_model=AIStatusOut)
def ai_status(service: ImportService = Depends(get_import_service)):
    """Check if Ollama AI is available for categorization."""
    result = service.check_ai_available()
    return AIStatusOut(**result)


@router.post("")
async def import_statement(
    files: list[UploadFile] = File(...),
    account_id: Optional[int] = Form(None),
    use_ai: bool = Form(False),
    auto_detect_account: bool = Form(True),
    service: ImportService = Depends(get_import_service),
    account_service: AccountService = Depends(get_account_service),
):
    """Import transactions from CSV/Excel bank statements."""
    results = []

    for file in files:
        content = await file.read()
        filename = file.filename or "statement.csv"

        # Try to detect account
        detected_account_id = None
        if auto_detect_account:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")
            detected_account_id, _ = service.detect_account(text, filename)

        # Use detected account, or fall back to provided account_id
        target_account_id = detected_account_id or account_id

        if not target_account_id:
            results.append({
                "filename": filename,
                "error": "Could not detect account. Please select manually or set account suffix.",
                "imported": 0,
            })
            continue

        # Verify account exists
        try:
            account = account_service.get(target_account_id)
        except DomainException as e:
            results.append({
                "filename": filename,
                "error": str(e.message),
                "imported": 0,
            })
            continue

        # Parse file
        transactions, bank_format = service.parse_file(content, filename)

        if not transactions:
            results.append({
                "filename": filename,
                "error": "No valid transactions found",
                "imported": 0,
            })
            continue

        # Import transactions
        try:
            result = service.import_transactions(
                transactions, target_account_id, use_ai=use_ai, filename=filename
            )
            result["filename"] = filename
            result["format"] = bank_format
            result["total_in_file"] = len(transactions)
            result["account_id"] = target_account_id
            result["account_name"] = account.name
            result["auto_detected"] = detected_account_id is not None
            results.append(result)
        except DomainException as e:
            results.append({
                "filename": filename,
                "error": str(e.message),
                "imported": 0,
            })

    # If single file, return flat result for backward compatibility
    if len(results) == 1:
        return results[0]

    return {"files": results, "total_imported": sum(r.get("imported", 0) for r in results)}


@router.post("/preview", response_model=PreviewOut)
async def preview_import(
    file: UploadFile = File(...),
    service: ImportService = Depends(get_import_service),
):
    """Preview transactions from a file without importing."""
    content = await file.read()
    filename = file.filename or "statement.csv"

    result = service.preview(content, filename)
    return PreviewOut(**result)


@router.get("/history")
def import_history(
    limit: int = 50,
    service: ImportService = Depends(get_import_service),
):
    """Get list of past imports."""
    return service.get_import_history(limit=limit)


@router.delete("/{batch_id}")
def revert_import(
    batch_id: int,
    service: ImportService = Depends(get_import_service),
):
    """Revert an import by deleting all its transactions."""
    try:
        return service.revert_import(batch_id)
    except DomainException as e:
        raise handle_domain_exception(e)
