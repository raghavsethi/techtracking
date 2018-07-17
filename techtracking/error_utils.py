import logging
from functools import wraps

from django.contrib import messages
from django.http import HttpRequest
from django.http import HttpResponseRedirect

logger = logging.getLogger(__name__)


class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.logger = logging.getLogger(__name__)
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception):
        self.logger.error("Exception occurred. Context:")
        self.logger.error("\tUser: %s", request.user)
        self.logger.error("\tPath: %s", request.method + " " + request.get_full_path())
        self.logger.error("\tReferrer: %s", request.META.get("HTTP_REFERER"))
        self.logger.error("\tUser-agent: %s", request.META.get("HTTP_USER_AGENT"))
        self.logger.error("\tGET Params: %s", dict(request.GET))
        self.logger.error("\tPOST Params: %s", dict(request.POST))
        return None


def error_redirect(request, message, path="/"):
    messages.error(request, message)

    user = "logged-out"
    if request.user.is_authenticated:
        user = request.user.email

    logging.debug("[%s] Returned error message to user: '%s'", user, message)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', path))


def success_redirect(request, message, path="/"):
    messages.success(request, message)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', path))


def require_http_post(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        if request.method != 'POST':
            logger.info("Received request with HTTP method " + request.method + " for view that only supports POST")
            return error_redirect(request, "Unable to process request, please try performing that action again.")
        return func(request, *args, **kwargs)
    return inner
