from flask import current_app


class NoGuestsError(Exception):
    """Raised when no guests are provided."""

    pass


class FileDoesNotExist(Exception):
    pass
