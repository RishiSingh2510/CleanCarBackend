class AppError(Exception):
    """An expected, user-facing error. Rendered as {"message": ..., "code": ...} with the given HTTP status."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers
