from datetime import datetime, timezone
from uuid import UUID

from supabase import Client
from supabase_auth.errors import AuthApiError, AuthError

from app.auth.service import AuthFailure, _client as _auth_client
from app.profile.schemas import ProfileIn, ProfileOut, ProfileUpdate


class ProfileError(Exception):
    """The profile could not be read or saved."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def create_profile(db: Client, profile: ProfileIn) -> ProfileOut:
    """Insert a new profile; the database generates its id."""
    try:
        data = db.table("profiles").insert(profile.model_dump(mode="json")).execute().data
    except Exception as e:
        if getattr(e, "code", None) == "23505":
            raise ProfileError(409, "A profile with this email already exists.") from e
        raise ProfileError(502, f"The profile could not be saved: {getattr(e, 'message', type(e).__name__)}") from e
    return ProfileOut(**data[0])


def update_profile(db: Client, profile_id: UUID, changes: ProfileUpdate) -> ProfileOut:
    """Change only the fields that were sent."""
    fields = changes.model_dump(mode="json", exclude_unset=True)
    if not fields:
        return get_profile(db, profile_id)
    try:
        data = db.table("profiles").update(fields).eq("profile_id", str(profile_id)).execute().data
    except Exception as e:
        raise ProfileError(502, f"The profile could not be saved: {getattr(e, 'message', type(e).__name__)}") from e
    if not data:
        raise ProfileError(404, "No such profile.")
    return ProfileOut(**data[0])


def set_bee(db: Client, profile_id: UUID, bee: str) -> ProfileOut:
    """Switch the profile's companion bee."""
    try:
        data = db.table("profiles").update({"bee": bee}).eq("profile_id", str(profile_id)).execute().data
    except Exception as e:
        raise ProfileError(502, f"The profile could not be saved: {getattr(e, 'message', type(e).__name__)}") from e
    if not data:
        raise ProfileError(404, "No such profile.")
    return ProfileOut(**data[0])


def _profile_by_email(db: Client, email: str) -> ProfileOut | None:
    """The profile synced with this email (also matched in lower case, since Supabase lower-cases emails)."""
    try:
        data = db.table("profiles").select("*").in_("email", list({email, email.lower()})).limit(1).execute().data
    except Exception as e:
        raise ProfileError(502, f"The profile could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    return ProfileOut(**data[0]) if data else None


def send_login_code(db: Client, email: str) -> None:
    """Email a one-time code to log in, only if a profile is synced with that email (nothing is created otherwise)."""
    email = email.strip()
    if _profile_by_email(db, email) is None:
        raise ProfileError(404, "No account found for that email. Use Get started to create one.")
    try:
        _auth_client().auth.sign_in_with_otp({"email": email, "options": {"should_create_user": False}})
    except AuthApiError as e:
        raise ProfileError(e.status if e.status in (400, 422, 429) else 400, e.message) from e
    except AuthError as e:
        raise ProfileError(502, e.message) from e
    except AuthFailure as e:
        raise ProfileError(e.status_code, e.message) from e


def confirm_login(db: Client, email: str, token: str) -> ProfileOut:
    """Check the code; if it is right, return the profile for that email (its profile_id is what the app keeps)."""
    email = email.strip()
    try:
        res = _auth_client().auth.verify_otp({"email": email, "token": token.strip(), "type": "email"})
    except AuthApiError as e:
        if e.status == 429:
            raise ProfileError(429, e.message) from e
        raise ProfileError(400, "The code is wrong or has expired.") from e
    except AuthError as e:
        raise ProfileError(502, e.message) from e
    except AuthFailure as e:
        raise ProfileError(e.status_code, e.message) from e
    if res is None or res.user is None:
        raise ProfileError(400, "The code is wrong or has expired.")
    profile = _profile_by_email(db, email)
    if profile is None:
        raise ProfileError(404, "No account found for that email. Use Get started to create one.")
    return profile


def save_suggestions(db: Client, profile_id: UUID, suggestions: dict) -> None:
    """Keep the roles last suggested to this profile (a JSON-ready RecommendResponse)."""
    try:
        db.table("profiles").update(
            {"suggested_roles": suggestions, "suggested_at": datetime.now(timezone.utc).isoformat()}
        ).eq("profile_id", str(profile_id)).execute()
    except Exception as e:
        raise ProfileError(502, f"The suggestions could not be saved: {getattr(e, 'message', type(e).__name__)}") from e


def get_suggestions(db: Client, profile_id: UUID) -> dict | None:
    """The roles last suggested to this profile, or None if there are none yet. 404 if the profile does not exist."""
    try:
        data = db.table("profiles").select("suggested_roles").eq("profile_id", str(profile_id)).limit(1).execute().data
    except Exception as e:
        raise ProfileError(502, f"The suggestions could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    if not data:
        raise ProfileError(404, "No such profile.")
    return data[0]["suggested_roles"]


def send_code(db: Client, profile_id: UUID, email: str) -> None:
    """Email a one-time code through Supabase Auth. Nothing is stored on the profile until the code is confirmed."""
    profile = get_profile(db, profile_id)  # 404 if there is no such profile
    if profile.email == email:
        raise ProfileError(409, "This profile already has that email.")
    taken = db.table("profiles").select("profile_id").eq("email", email).limit(1).execute().data
    if taken:
        raise ProfileError(409, "A profile with this email already exists.")
    try:
        _auth_client().auth.sign_in_with_otp({"email": email})
    except AuthApiError as e:
        raise ProfileError(e.status if e.status in (400, 422, 429) else 400, e.message) from e
    except AuthError as e:
        raise ProfileError(502, e.message) from e
    except AuthFailure as e:
        raise ProfileError(e.status_code, e.message) from e


def confirm_code(db: Client, profile_id: UUID, email: str, token: str) -> ProfileOut:
    """Check the code; if it is right for this email, write the email onto the profile."""
    get_profile(db, profile_id)
    try:
        res = _auth_client().auth.verify_otp({"email": email, "token": token, "type": "email"})
    except AuthApiError as e:
        if e.status == 429:
            raise ProfileError(429, e.message) from e
        raise ProfileError(400, "The code is wrong or has expired.") from e
    except AuthError as e:
        raise ProfileError(502, e.message) from e
    except AuthFailure as e:
        raise ProfileError(e.status_code, e.message) from e
    if res is None or res.user is None:
        raise ProfileError(400, "The code is wrong or has expired.")
    try:
        data = db.table("profiles").update({"email": email}).eq("profile_id", str(profile_id)).execute().data
    except Exception as e:
        if getattr(e, "code", None) == "23505":
            raise ProfileError(409, "A profile with this email already exists.") from e
        raise ProfileError(502, f"The profile could not be saved: {getattr(e, 'message', type(e).__name__)}") from e
    return ProfileOut(**data[0])


def get_profile(db: Client, profile_id: UUID) -> ProfileOut:
    try:
        data = db.table("profiles").select("*").eq("profile_id", str(profile_id)).limit(1).execute().data
    except Exception as e:
        raise ProfileError(502, f"The profile could not be read: {getattr(e, 'message', type(e).__name__)}") from e
    if not data:
        raise ProfileError(404, "No such profile.")
    return ProfileOut(**data[0])
