from fastapi import Request, status
from fastapi.responses import JSONResponse
from logger import logger


class AWSScannerError(Exception):
    """Base exception class for AWS scanner errors."""
    def __init__(self, message: str = "An AWS scanner error occurred."):
        self.message = message
        super().__init__(self.message)


class AWSCLINotInstalledError(AWSScannerError):
    """Raised when AWS CLI ('aws') is not installed or not found on system PATH."""
    def __init__(self, message: str = "AWS CLI ('aws') is not installed or not found in system PATH."):
        super().__init__(message)


class AWSNotConfiguredError(AWSScannerError):
    """Raised when AWS CLI credentials are missing or unconfigured."""
    def __init__(self, message: str = "AWS CLI is not configured. Please run 'aws configure' to set up credentials."):
        super().__init__(message)


class AWSInvalidCredentialsError(AWSScannerError):
    """Raised when AWS CLI credentials are expired or invalid."""
    def __init__(self, message: str = "Invalid or expired AWS credentials."):
        super().__init__(message)


class AWSInvalidRegionError(AWSScannerError):
    """Raised when an invalid AWS region name is specified."""
    def __init__(self, message: str = "Invalid AWS region specified."):
        super().__init__(message)


class AWSCLITimeoutError(AWSScannerError):
    """Raised when an AWS CLI subprocess command times out."""
    def __init__(self, message: str = "AWS CLI command timed out after 30 seconds."):
        super().__init__(message)


class AWSCLIExecutionError(AWSScannerError):
    """Raised when an AWS CLI subprocess command fails with an unexpected exit code."""
    def __init__(self, message: str = "AWS CLI execution failed."):
        super().__init__(message)


def register_exception_handlers(app):
    """Registers exception handlers with FastAPI application."""

    @app.exception_handler(AWSCLINotInstalledError)
    async def cli_not_installed_handler(request: Request, exc: AWSCLINotInstalledError):
        logger.error(f"503 Service Unavailable - AWS CLI missing: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "AWS_CLI_NOT_INSTALLED", "message": exc.message}
        )

    @app.exception_handler(AWSNotConfiguredError)
    async def not_configured_handler(request: Request, exc: AWSNotConfiguredError):
        logger.error(f"401 Unauthorized - AWS CLI unconfigured: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "AWS_NOT_CONFIGURED", "message": exc.message}
        )

    @app.exception_handler(AWSInvalidCredentialsError)
    async def invalid_credentials_handler(request: Request, exc: AWSInvalidCredentialsError):
        logger.error(f"401 Unauthorized - Invalid credentials: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "INVALID_AWS_CREDENTIALS", "message": exc.message}
        )

    @app.exception_handler(AWSInvalidRegionError)
    async def invalid_region_handler(request: Request, exc: AWSInvalidRegionError):
        logger.error(f"400 Bad Request - Invalid region: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "INVALID_AWS_REGION", "message": exc.message}
        )

    @app.exception_handler(AWSCLITimeoutError)
    async def timeout_handler(request: Request, exc: AWSCLITimeoutError):
        logger.error(f"504 Gateway Timeout - AWS CLI timeout: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={"error": "AWS_CLI_TIMEOUT", "message": exc.message}
        )

    @app.exception_handler(AWSScannerError)
    async def generic_scanner_handler(request: Request, exc: AWSScannerError):
        logger.error(f"500 Internal Server Error - Scanner error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "AWS_SCANNER_ERROR", "message": exc.message}
        )
