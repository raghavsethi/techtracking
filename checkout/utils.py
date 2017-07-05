from django.http import HttpResponseRedirect
from django.contrib import messages

import logging
logger = logging.getLogger(__name__)


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
