"""Domain exceptions for business logic errors."""


class DomainException(Exception):
    """Base exception for domain errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(DomainException):
    """Raised when a requested entity is not found."""

    def __init__(self, entity: str, entity_id: int):
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} {entity_id} not found", "NOT_FOUND")


class DuplicateError(DomainException):
    """Raised when attempting to create a duplicate entity."""

    def __init__(self, message: str):
        super().__init__(message, "DUPLICATE")


class ValidationError(DomainException):
    """Raised when validation fails."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class TransferError(DomainException):
    """Raised for transfer-related validation errors."""

    def __init__(self, message: str):
        super().__init__(message, "TRANSFER_ERROR")


class ImportError(DomainException):
    """Raised for import-related errors."""

    def __init__(self, message: str):
        super().__init__(message, "IMPORT_ERROR")


class CategoryError(DomainException):
    """Raised for category-related errors."""

    def __init__(self, message: str):
        super().__init__(message, "CATEGORY_ERROR")
