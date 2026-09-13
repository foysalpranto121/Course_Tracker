import logging
import time
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils import translation
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class IPBlockingMiddleware(MiddlewareMixin):
    """
    1. IP Blocking Middleware:
    Blocks requests coming from IP addresses defined in settings.BLOCKED_IPS.
    """

    def process_request(self, request):
        blocked_ips = getattr(settings, "BLOCKED_IPS", [])

        # Extract client IP (supporting reverse proxies)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")

        if ip in blocked_ips:
            logger.warning(f"Access Denied for blocked IP: {ip}")
            return HttpResponseForbidden("403 Forbidden: Access from your IP address has been blocked.")

        return None


class GlobalAuthCheckMiddleware(MiddlewareMixin):
    """
    2. Global Authentication Check Middleware:
    Automatically redirects unauthenticated requests away from protected routes.
    """

    EXEMPT_PREFIXES = [
        "/landing",
        "/guest-signin",
        "/signin",
        "/signup",
        "/admin",
        "/static",
        "/media",
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            path = request.path_info or request.path or "/"
            
            # Root path '/' or '' is public landing page
            if path in ["", "/"]:
                return None

            # Exempt prefixes
            if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
                return None

            messages.warning(request, "Please sign in to access this page.")
            return redirect(f"/signin/?next={path}")

        return None




class RequestResponseLoggingMiddleware(MiddlewareMixin):
    """
    3. Request / Response Logging Middleware:
    Logs incoming HTTP requests and outgoing response status codes.
    """

    def process_request(self, request):
        user = request.user.username if request.user.is_authenticated else "Anonymous"
        ip = request.META.get("REMOTE_ADDR", "unknown")
        logger.info(f"Incoming Request: {request.method} {request.path_info} | User: {user} | IP: {ip}")
        return None

    def process_response(self, request, response):
        user = request.user.username if request.user.is_authenticated else "Anonymous"
        logger.info(f"Outgoing Response: {request.method} {request.path_info} | Status: {response.status_code} | User: {user}")
        return response


class LanguageAndSessionManagementMiddleware(MiddlewareMixin):
    """
    4. Language & Session Management Middleware:
    Manages session language preference and tracks user activity timestamps.
    """

    def process_request(self, request):
        # Language Management via query parameter 'lang' or session
        lang = request.GET.get("lang")
        if lang:
            translation.activate(lang)
            request.session["django_language"] = lang
        elif "django_language" in request.session:
            translation.activate(request.session["django_language"])

        # Session Management: Track last activity timestamp
        if request.user.is_authenticated:
            request.session["last_activity"] = int(time.time())

        return None


class PerformanceTimingMiddleware(MiddlewareMixin):
    """
    5. Performance Timing Middleware:
    Measures processing duration and attaches X-Performance-Timing-Ms header.
    """

    def process_request(self, request):
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, "_start_time"):
            duration_ms = (time.time() - request._start_time) * 1000
            response["X-Performance-Timing-Ms"] = f"{duration_ms:.2f}ms"
            if duration_ms > 500:
                logger.warning(f"Slow Request: {request.method} {request.path_info} took {duration_ms:.2f}ms")
        return response
