from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime

class BugFlowException(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ResourceNotFound(BugFlowException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class DuplicateKey(BugFlowException):
    def __init__(self, message: str = "Duplicate key constraint violated"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

class BadRequest(BugFlowException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

class InvalidTransition(BugFlowException):
    def __init__(self, message: str = "Invalid status transition"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)

class Unauthorized(BugFlowException):
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)

class Forbidden(BugFlowException):
    def __init__(self, message: str = "Forbidden operation"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)

def format_error_response(status_code: int, message: str, path: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status_code,
            "message": message,
            "path": path
        }
    )

def setup_exception_handlers(app):
    @app.exception_handler(BugFlowException)
    async def bugflow_exception_handler(request: Request, exc: BugFlowException):
        return format_error_response(exc.status_code, exc.message, request.url.path)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return format_error_response(exc.status_code, exc.detail, request.url.path)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Format validation error message cleanly
        errors = []
        for error in exc.errors():
            field = " -> ".join(map(str, error.get("loc", [])))
            msg = error.get("msg", "Invalid value")
            errors.append(f"{field}: {msg}")
        message = "; ".join(errors)
        return format_error_response(status.HTTP_400_BAD_REQUEST, f"Validation failed: {message}", request.url.path)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return format_error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, f"An unexpected error occurred: {str(exc)}", request.url.path)
