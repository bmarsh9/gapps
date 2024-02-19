from abc import ABC

class CustomError(ABC, Exception):
    def __init__(self, message="Internal Server Error", status=500):
        self.message = message
        self.status = status
        super().__init__(self.message)

# 403 UNAUTHORISED

class AuthorizationError(CustomError):
    def __init__(self, message="Unauthorized access", status=403):
        super().__init__(message, status)

# 404 NOT FOUND

class ProjectNotFound(CustomError):
    def __init__(self, message="Project not found", status=404):
        super().__init__(message, status)

class TenantNotFound(CustomError):
    def __init__(self, message="Tenant not found", status=404):
        super().__init__(message, status)
