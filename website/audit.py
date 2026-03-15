from contextvars import ContextVar


_current_audit_user = ContextVar("current_audit_user", default=None)


def set_current_audit_user(user):
    return _current_audit_user.set(user)


def get_current_audit_user():
    return _current_audit_user.get()


def reset_current_audit_user(token):
    _current_audit_user.reset(token)
