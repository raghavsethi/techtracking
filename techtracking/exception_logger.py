import logging

from django.http import HttpRequest


class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.logger = logging.getLogger(__name__)
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception):
        self.logger.error("Exception occurred. Context:")
        self.logger.error("\tUser: %s", request.user)
        self.logger.error("\tPath: %s", request.method + request.get_full_path())
        self.logger.error("\tReferrer: %s", request.META.get("HTTP_REFERER"))
        self.logger.error("\tUser-agent: %s", request.META.get("HTTP_USER_AGENT"))
        self.logger.error("\tGET Params: %s", dict(request.GET))
        self.logger.error("\tPOST Params: %s", dict(request.POST))
        return None
