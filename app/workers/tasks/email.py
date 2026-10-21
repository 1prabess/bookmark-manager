import hashlib
import secrets

from celery import Task, shared_task  # type: ignore[import-untyped]

from app.core.email import send_email


def render_welcome_email(*, to_email: str) -> tuple[str, str]:
    subject = "Welcome to Bookmark Manager"
    html = f"""
    <html><body>
      <h1>Welcome, {to_email}!</h1>
      <p>Your account is ready. Save your first link and tag it.</p>
    </body></html>
    """.strip()
    return subject, html


def render_password_reset_email(*, to_email: str, reset_token: str) -> tuple[str, str]:
    subject = "Reset your Bookmark Manager password"
    html = f"""
    <html><body>
      <h1>Password reset</h1>
      <p>Click the link below to reset your password. The link expires in 30 minutes.</p>
      <p><a href="https://your-app.example.com/reset?token={reset_token}">Reset password</a></p>
      <p>If you didn't request this, ignore this email.</p>
    </body></html>
    """.strip()
    return subject, html


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="email.send_welcome",
)
def send_welcome_email(self: Task, to_email: str) -> str:
    subject, html = render_welcome_email(to_email=to_email)
    try:
        send_email(to=to_email, subject=subject, html_body=html)
        return f"welcome_email_sent:{to_email}"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="email.send_password_reset",
)
def send_password_reset_email(self, to_email: str, reset_token: str) -> str:
    subject, html = render_password_reset_email(
        to_email=to_email, reset_token=reset_token)
    try:
        send_email(to=to_email, subject=subject, html_body=html)
        return f"reset_email_sent:{to_email}"
    except Exception as exc:
        raise self.retry(exc=exc)


def queue_send_welcome(*, to_email: str) -> None:
    send_welcome_email.delay(to_email)  # type: ignore[reportCallIssue]


def queue_send_password_reset(*, to_email: str, reset_token: str) -> None:
    send_password_reset_email.delay(to_email, reset_token)  # type: ignore


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
