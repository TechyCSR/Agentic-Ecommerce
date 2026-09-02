class ApiError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message, code=None, status_code=None, details=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(ApiError):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(ApiError):
    status_code = 401
    code = "UNAUTHORIZED"


class ValidationError(ApiError):
    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(ApiError):
    status_code = 409
    code = "CONFLICT"
