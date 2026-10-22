from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthError

from app.auth.schemas import Credentials, RegisterOut, SessionOut, UserOut
from app.config import get_settings


class AuthFailure(Exception):
    """A Supabase auth problem to report to the caller; carries the HTTP status."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _client() -> Client:
    """A new client per call: sign-in stores the session on the client, so sharing one would mix users."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise AuthFailure(503, "SUPABASE_URL and SUPABASE_KEY are not set.")
    return create_client(settings.supabase_url, settings.supabase_key)


def _user(u) -> UserOut:
    return UserOut(id=str(u.id), email=u.email)


def _session(s, user) -> SessionOut:
    return SessionOut(
        access_token=s.access_token,
        refresh_token=s.refresh_token,
        expires_in=s.expires_in,
        user=_user(user),
    )


def register(body: Credentials) -> RegisterOut:
    try:
        res = _client().auth.sign_up({"email": body.email, "password": body.password})
    except AuthApiError as e:
        raise AuthFailure(e.status if e.status in (400, 422, 429) else 400, e.message)
    except AuthError as e:
        raise AuthFailure(502, e.message)
    if res.user is None:
        raise AuthFailure(400, "Sign-up did not return a user.")
    if res.session is None:
        return RegisterOut(user=_user(res.user), session=None, message="Check your email to confirm the account, then log in.")
    return RegisterOut(user=_user(res.user), session=_session(res.session, res.user), message="Account created.")


def login(body: Credentials) -> SessionOut:
    try:
        res = _client().auth.sign_in_with_password({"email": body.email, "password": body.password})
    except AuthApiError as e:
        if e.status == 429:
            raise AuthFailure(429, e.message)
        raise AuthFailure(401, "Invalid email or password, or the email is not confirmed yet.")
    except AuthError as e:
        raise AuthFailure(502, e.message)
    return _session(res.session, res.user)


def current_user(access_token: str) -> UserOut:
    """Ask Supabase to validate the access token and return its user."""
    try:
        res = _client().auth.get_user(access_token)
    except AuthError:
        raise AuthFailure(401, "Invalid or expired token.")
    if res is None or res.user is None:
        raise AuthFailure(401, "Invalid or expired token.")
    return _user(res.user)
