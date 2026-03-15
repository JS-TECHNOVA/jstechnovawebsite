from .audit import reset_current_audit_user, set_current_audit_user


class AuditUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_audit_user(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            reset_current_audit_user(token)
