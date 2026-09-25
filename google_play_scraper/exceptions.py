class GooglePlayScraperException(Exception):
    pass


class NotFoundError(GooglePlayScraperException):
    pass


class ExtraHTTPError(GooglePlayScraperException):
    pass


class SearchResultParseError(GooglePlayScraperException):
    """Raised when the search response is missing its results dataset (ds:4), i.e. a truncated response."""

    pass
