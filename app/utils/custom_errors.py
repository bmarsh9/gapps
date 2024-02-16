from abc import ABC

class CustomError(ABC, Exception):
    def __init__(self, message="Internal Server Error", status=500):
        self.message = message
        self.status = status
        super().__init__(self.message)

class AuthorizationError(CustomError):
    def __init__(self, message="Unauthorized access", status=403):
        super().__init__(message, status)

class TenantNotFound(CustomError):
    def __init__(self, message="Tenant not found", status=404):
        super().__init__(message, status)