"""Tracking and revoking a user's signed-in sessions."""

from importlib import import_module

from django.conf import settings

from .models import UserSession
from .security import get_client_ip, get_user_agent


def _store(session_key=None):
    return import_module(settings.SESSION_ENGINE).SessionStore(session_key)


def track(request, user):
    """Remember the current session for this user (call right after login())."""
    if not request.session.session_key:
        request.session.save()
    UserSession.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            "user": user,
            "ip_address": get_client_ip(request),
            "user_agent": get_user_agent(request),
        },
    )


def rekey(old_key, request):
    """The session key changed (e.g. after update_session_auth_hash); follow it."""
    if old_key and old_key != request.session.session_key:
        UserSession.objects.filter(session_key=old_key).update(session_key=request.session.session_key)


def revoke(user_session):
    _store(user_session.session_key).delete()
    user_session.delete()


def revoke_all(user, except_key=None):
    """Sign the user out everywhere, optionally keeping one session. Returns how many were ended."""
    count = 0
    for user_session in UserSession.objects.filter(user=user).exclude(session_key=except_key or ""):
        revoke(user_session)
        count += 1
    return count


def active_sessions(user):
    """The user's live sessions; records whose session has ended are tidied away."""
    live = []
    for user_session in UserSession.objects.filter(user=user):
        if _store(user_session.session_key).exists(user_session.session_key):
            live.append(user_session)
        else:
            user_session.delete()
    return live
