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

# 400 BAD REQUEST

class ValidationError(CustomError):
    def __init__(self, message="Submitted data could not be validated", status=HttpResponseStatus.BAD_REQUEST):
        super().__init__(message, status)

# 403 FORBIDDEN

class AuthorizationError(CustomError):
    def __init__(self, message="Unauthorized access", status=HttpResponseStatus.FORBIDDEN):
        super().__init__(message, status)

# 404 NOT FOUND
        
class LocaleNotFound(CustomError):
    def __init__(self, message="Locale not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class ProjectCommentNotFound(CustomError):
    def __init__(self, message="Project comment not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class ProjectControlNotFound(CustomError):
    def __init__(self, message="Project control not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class ProjectNotFound(CustomError):
    def __init__(self, message="Project not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class TenantNotFound(CustomError):
    def __init__(self, message="Tenant not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

class UserNotFound(CustomError):
    def __init__(self, message="User not found", status=HttpResponseStatus.NOT_FOUND):
        super().__init__(message, status)

# 500 INTERNAL SERVER ERROR

class PostgresError(CustomError):
    def __init__(self, message="Postgres encountered a critical error and was unable to finish the transaction"):
        super().__init__(message)