from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from supabase import Client

from app.deps import get_supabase_admin
from app.profile import service
from app.profile.schemas import Bee, LoginIn, LoginVerifyIn, ProfileIn, ProfileOut, ProfileUpdate, SyncIn, SyncOut, SyncVerifyIn

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileIn, db: Client = Depends(get_supabase_admin)):
    """Create a profile. No login needed. name, stage, skills and experience are required; interests (ids from GET /interests) are optional; email is optional. The profile_id is generated and returned. A second POST with the same email is rejected with 409."""
    try:
        return service.create_profile(db, body)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)


@router.post("/sync", response_model=SyncOut)
def sync_email(body: SyncIn, db: Client = Depends(get_supabase_admin)):
    """Step 1 of binding an email: Supabase emails a one-time code to the address. The profile is not changed yet. 404 if the profile does not exist; 409 if the email is already bound to a profile."""
    try:
        service.send_code(db, body.profile_id, body.email)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    return SyncOut(message="Code sent. Confirm it with POST /profile/sync/verify.")


@router.post("/sync/verify", response_model=ProfileOut)
def verify_sync(body: SyncVerifyIn, db: Client = Depends(get_supabase_admin)):
    """Step 2: send the code from the email. If it is right, the email is written to the profile and the updated profile is returned."""
    try:
        return service.confirm_code(db, body.profile_id, body.email, body.token)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)


@router.post("/login", response_model=SyncOut)
def login(body: LoginIn, db: Client = Depends(get_supabase_admin)):
    """Step 1 of logging in to an existing profile: Supabase emails a one-time code to the address it was synced with. 404 if no profile has that email (nothing is sent or created)."""
    try:
        service.send_login_code(db, body.email)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
    return SyncOut(message="Code sent. Confirm it with POST /profile/login/verify.")


@router.post("/login/verify", response_model=ProfileOut)
def verify_login(body: LoginVerifyIn, db: Client = Depends(get_supabase_admin)):
    """Step 2: send the code from the email. If it is right, the profile is returned; keep its profile_id to use the other /profile and /roadmap routes. 400 if the code is wrong or expired."""
    try:
        return service.confirm_login(db, body.email, body.token)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)


# Declared before /{profile_id} so "bee" is not read as an id.
@router.patch("/bee", response_class=PlainTextResponse)
def change_bee(
    profile_id: UUID = Query(description="The profile_id returned from POST /profile"),
    bee: Bee = Query(description="The companion to switch to"),
    db: Client = Depends(get_supabase_admin),
):
    """Switch a profile's companion bee (Libbee, Phoebee, Tobee or Barnabee; 422 otherwise). Returns the new bee's name as plain text; 404 if there is no such profile."""
    try:
        return service.set_bee(db, profile_id, bee).bee
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)


@router.get("/{profile_id}", response_model=ProfileOut)
def read_profile(profile_id: UUID, db: Client = Depends(get_supabase_admin)):
    """Read a profile by the profile_id returned from POST. 404 if there is none."""
    try:
        return service.get_profile(db, profile_id)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: UUID, body: ProfileUpdate, db: Client = Depends(get_supabase_admin)):
    """Update a profile. Only the fields sent are changed; the email is changed through /profile/sync. Returns the updated profile; 404 if there is none."""
    try:
        return service.update_profile(db, profile_id, body)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
