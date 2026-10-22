from uuid import UUID

from supabase import Client
from supabase_auth.errors import AuthApiError, AuthError

from app.auth.service import AuthFailure, _client as _auth_client
from app.profile.schemas import ProfileIn, ProfileOut


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
