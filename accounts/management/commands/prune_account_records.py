from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import LoginLockout, RateLimit, SecurityEvent, UserSession


class Command(BaseCommand):
    help = (
        "Delete expired rate-limit counters, old lockouts, ended sessions and security events "
        "older than ACCOUNTS_SECURITY_EVENT_RETENTION_DAYS. Run daily (e.g. a Render cron job)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.ACCOUNTS_PRUNE_BATCH_SIZE,
            help="Maximum rows deleted per table per run (keeps each run small; a backlog shows up in the output).",
        )

    def _delete_batch(self, queryset, batch_size):
        pks = list(queryset.values_list("pk", flat=True)[:batch_size])
        deleted = queryset.model.objects.filter(pk__in=pks).delete()[0] if pks else 0
        backlog = len(pks) == batch_size and queryset.exists()
        return deleted, backlog

    def handle(self, *args, batch_size, **options):
        now = timezone.now()
        retention = timedelta(days=settings.ACCOUNTS_SECURITY_EVENT_RETENTION_DAYS)
        longest_window = max(window for _, window in settings.ACCOUNTS_RATE_LIMITS.values())
        live_keys = Session.objects.filter(expire_date__gt=now).values("session_key")

        jobs = {
            "security events": SecurityEvent.objects.filter(created_at__lt=now - retention),
            "rate-limit counters": RateLimit.objects.filter(window_start__lt=now - timedelta(seconds=longest_window)),
            "lockouts": LoginLockout.objects.filter(
                last_failure_at__lt=now - timedelta(seconds=settings.ACCOUNTS_LOCKOUT_RESET_SECONDS)
            ),
            "ended sessions": UserSession.objects.exclude(session_key__in=live_keys),
            "expired Django sessions": Session.objects.filter(expire_date__lte=now),
        }
        for label, queryset in jobs.items():
            deleted, backlog = self._delete_batch(queryset, batch_size)
            note = " (batch limit reached; more remain, run again)" if backlog else ""
            self.stdout.write(f"{label}: deleted {deleted}{note}")
