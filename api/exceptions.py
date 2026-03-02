"""API-level exceptions for clean error handling."""

class APIError(Exception):
    """Base API error."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class AuthenticationError(APIError):
    """Authentication failed."""
    pass

class RateLimitError(APIError):
    """Rate limited by API."""
    def __init__(self, retry_after=5):
        super().__init__(f"Rate limited, retry after {retry_after}s")
        self.retry_after = retry_after

class ReportTimeoutError(APIError):
    """Report generation timed out."""
    pass

class InvalidCredentialsError(APIError):
    """Credentials missing or invalid."""
    pass
