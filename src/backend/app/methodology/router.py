from fastapi import APIRouter

from app.methodology import service

router = APIRouter(prefix="/methodology", tags=["methodology"])


@router.get("")
def get_methodology():
    """How every forecast works: source, what is measured, model, test results, uncertainty and limitations, read from the pipelines' outputs. A field they don't hold is null; nothing is estimated here."""
    return service.describe()
