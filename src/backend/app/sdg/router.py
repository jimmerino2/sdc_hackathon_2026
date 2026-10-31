from fastapi import APIRouter, HTTPException

from app.sdg import service
from app.sdg.schemas import RoleSdg

router = APIRouter(prefix="/sdg", tags=["sdg"])


@router.get("/roles/{onet_code}", response_model=RoleSdg)
def role_sdg(onet_code: str):
    """The UN SDGs a role's work serves: its main goal, the other relevant goals and the targets (sub-goals, e.g. 8.2) behind them, plus the same for each of the role's skills. 404 if the role has none on record."""
    out = service.role_sdg(onet_code)
    if not out:
        raise HTTPException(404, f"No SDGs on record for {onet_code}")
    return out
