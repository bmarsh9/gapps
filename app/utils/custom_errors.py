from abc import ABC

from app.utils.enums import HttpResponseStatus

class CustomError(ABC, Exception):
    def __init__(
            self,
            message: str = "Internal Server Error",
            status: HttpResponseStatus = HttpResponseStatus.INTERNAL_SERVER_ERROR,
        ):
        self.message = message
        self.status = status.value
        super().__init__(self.message)

# 403 UNAUTHORISED

class AuthorizationError(CustomError):
    def __init__(self, message="Unauthorized access", status=HttpResponseStatus.UNAUTHORIZED):
        super().__init__(message, status)

# 404 NOT FOUND

class ProjectNotFound(CustomError):
    def __init__(self, message="Project not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class TenantNotFound(CustomError):
    def __init__(self, message="Tenant not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

# 500 INTERNAL SERVER ERROR

class PostgresError(CustomError):
    def __init__(self, message="Postgres encountered a critical error and was unable to finish the transaction"):
        super().__init__(message)