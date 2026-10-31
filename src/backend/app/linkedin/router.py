from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.linkedin import service
from app.linkedin.schemas import ShareStart, ShareStarted, Status

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


@router.get("/status", response_model=Status)
def status():
    """Whether posting to LinkedIn is set up (the app keys are present), so the page knows to show the Post button."""
    return Status(enabled=service.enabled())


@router.post("/share", response_model=ShareStarted)
def start_share(body: ShareStart):
    """Keep the learner's draft (text and PNG) for 15 minutes and return the LinkedIn address where they sign in and allow one post.

    Nothing is posted yet: LinkedIn sends the browser back to /linkedin/callback after the learner agrees. 422 for a bad draft,
    503 if the server has no LinkedIn app keys.
    """
    try:
        return ShareStarted(authorize_url=service.start(body.text, body.image_base64))
    except service.ShareError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/callback", include_in_schema=False)
def callback(code: str | None = None, state: str | None = None, error: str | None = Query(None)):
    """Where LinkedIn sends the browser back. Posts the draft, then returns the browser to the app with the result in the address."""
    back = get_settings().linkedin_return_url

    def to_app(**params: str) -> RedirectResponse:
        sep = "&" if "?" in back else "?"
        return RedirectResponse(f"{back}{sep}{urlencode(params)}", status_code=303)

    if error:  # the learner said no, or LinkedIn refused
        return to_app(linkedin="cancelled")
    if not code or not state:
        return to_app(linkedin="error", reason="LinkedIn didn’t send back what we need. Try again.")
    try:
        return to_app(linkedin="posted", post=service.finish(code, state))
    except service.ShareError as e:
        return to_app(linkedin="error", reason=e.message)
