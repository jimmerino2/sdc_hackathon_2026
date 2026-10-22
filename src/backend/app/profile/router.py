from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from app.deps import get_supabase_admin
from app.profile import service
from app.profile.schemas import ProfileIn, ProfileOut, SyncIn, SyncOut, SyncVerifyIn

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileIn, db: Client = Depends(get_supabase_admin)):
    """Create a profile. No login needed. name, stage, concerns, skills and experience are required; email is optional. The profile_id is generated and returned. A second POST with the same email is rejected with 409."""
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


@router.get("/{profile_id}", response_model=ProfileOut)
def read_profile(profile_id: UUID, db: Client = Depends(get_supabase_admin)):
    """Read a profile by the profile_id returned from POST. 404 if there is none."""
    try:
        return service.get_profile(db, profile_id)
    except service.ProfileError as e:
        raise HTTPException(e.status_code, e.message)
