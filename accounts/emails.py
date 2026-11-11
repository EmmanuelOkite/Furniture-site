import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from . import tokens

logger = logging.getLogger("accounts.security")


def send_account_email(user, template, request, **context):
    """
    Send `accounts/emails/<template>_subject.txt` / `_body.txt` to the user.
    Failures are logged (without the address) and never shown to the visitor,
    so the public response is the same whether or not an email went out.
    """
    context = {
        "user": user,
        "site_name": settings.ACCOUNTS_SITE_NAME,
        "site_url": request.build_absolute_uri("/"),
        **context,
    }
    subject = render_to_string(f"accounts/emails/{template}_subject.txt", context).strip()
    body = render_to_string(f"accounts/emails/{template}_body.txt", context)
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        logger.exception("email_send_failed template=%s user_id=%s", template, user.pk)
        return False
    return True


def send_reactivation_email(user, request):
    token = tokens.make_token(user, tokens.REACTIVATE)
    link = request.build_absolute_uri(reverse("accounts:reactivate_confirm", args=[token]))
    hours = settings.ACCOUNTS_REACTIVATION_TIMEOUT // 3600
    return send_account_email(user, "reactivate", request, link=link, hours=hours)
