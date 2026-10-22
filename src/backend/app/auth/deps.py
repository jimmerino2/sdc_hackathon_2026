from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import service
from app.auth.schemas import UserOut

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UserOut:
    """Use on any route that needs a logged-in user: `user: UserOut = Depends(get_current_user)`."""
    if creds is None:
        raise HTTPException(401, "Missing bearer token.", headers={"WWW-Authenticate": "Bearer"})
    try:
        return service.current_user(creds.credentials)
    except service.AuthFailure as e:
        raise HTTPException(e.status_code, e.message, headers={"WWW-Authenticate": "Bearer"})
