"""Common response schemas."""

from pydantic import BaseModel


class OkResponse(BaseModel):
    """Generic success response."""
    ok: bool = True


class IdResponse(BaseModel):
    """Response containing a created entity ID."""
    id: int


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    code: str = "ERROR"
