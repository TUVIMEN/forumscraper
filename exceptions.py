class ForumScraperException(Exception):
    pass


class RequestError(ForumScraperException):
    pass


class AlreadyVisitedError(ForumScraperException):
    pass
