class GooglePlayScraperException(Exception):
    pass


class NotFoundError(GooglePlayScraperException):
    pass


class ExtraHTTPError(GooglePlayScraperException):
    pass


class SearchResultParseError(GooglePlayScraperException):
    """Raised when the search response is missing its results dataset (ds:4).

    A well-formed response always contains ds:4, even for zero-match queries, so a
    missing block signals a truncated or malformed response rather than "no apps".
    Callers should treat this as a transient failure and retry.
    """

    pass
