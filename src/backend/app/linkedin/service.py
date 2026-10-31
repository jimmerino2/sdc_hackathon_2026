"""Post one learner-approved text and image to their own LinkedIn feed.

The flow: the page sends the draft (start); the learner signs in at LinkedIn and allows one post; LinkedIn sends the browser
back with a code (finish), which is exchanged for a token, used once to upload the image and create the post, and then dropped.
The token is never stored, and nothing is posted unless the learner went through LinkedIn's consent screen for this draft.
"""
import base64
import datetime
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import quote, urlencode

import httpx

from app.config import get_settings

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
API = "https://api.linkedin.com"
VERSION_MONTHS_BACK = 8  # LinkedIn keeps a version for about a year, so the recent months include one it still serves
SCOPES = "openid profile w_member_social"
DRAFT_TTL_SECONDS = 15 * 60
MAX_TEXT = 3000
MAX_IMAGE_BYTES = 3 * 1024 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TIMEOUT = httpx.Timeout(20, connect=5)


class ShareError(Exception):
    """Something went wrong; `message` can be shown to the learner as is."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message, self.status_code = message, status_code


@dataclass
class Draft:
    text: str
    image: bytes
    created: float


_drafts: dict[str, Draft] = {}
_lock = threading.Lock()


def enabled() -> bool:
    s = get_settings()
    return bool(s.linkedin_client_id and s.linkedin_client_secret and s.linkedin_redirect_uri)


def _forget_old() -> None:
    cutoff = time.time() - DRAFT_TTL_SECONDS
    for state in [k for k, d in _drafts.items() if d.created < cutoff]:
        del _drafts[state]


def validate(text: str, image_base64: str) -> tuple[str, bytes]:
    """The cleaned text and the PNG bytes, or a ShareError saying what is wrong."""
    text = (text or "").strip()
    if not text:
        raise ShareError("Write something to post.", 422)
    if len(text) > MAX_TEXT:
        raise ShareError(f"LinkedIn posts are limited to {MAX_TEXT:,} characters. Shorten it.", 422)
    raw = (image_base64 or "").split(",", 1)[-1]  # accept a data: URL
    try:
        image = base64.b64decode(raw, validate=True)
    except ValueError:
        raise ShareError("The image couldn’t be read.", 422) from None
    if not image.startswith(PNG_MAGIC):
        raise ShareError("The image must be a PNG.", 422)
    if len(image) > MAX_IMAGE_BYTES:
        raise ShareError("The image is too large.", 422)
    return text, image


def start(text: str, image_base64: str) -> str:
    """Keep the draft for a few minutes and return the LinkedIn address the learner must visit to allow the post."""
    if not enabled():
        raise ShareError("Posting to LinkedIn isn’t set up on this server.", 503)
    text, image = validate(text, image_base64)
    state = secrets.token_urlsafe(24)
    with _lock:
        _forget_old()
        _drafts[state] = Draft(text, image, time.time())
    s = get_settings()
    query = urlencode({"response_type": "code", "client_id": s.linkedin_client_id, "redirect_uri": s.linkedin_redirect_uri,
                       "state": state, "scope": SCOPES})
    return f"{AUTH_URL}?{query}"


def take_draft(state: str) -> Draft:
    """The draft for this sign-in, removed so it can't be used twice."""
    with _lock:
        _forget_old()
        draft = _drafts.pop(state, None)
    if draft is None:
        raise ShareError("That sign-in expired. Open the share dialog and try again.", 400)
    return draft


_RESERVED = re.compile(r"([\\|{}@\[\]()<>#*_~])")
_HASHTAG = re.compile(r"#([A-Za-z0-9]+)")


def commentary(text: str) -> str:
    """The text in LinkedIn's post format: its reserved characters escaped, and #tags written as real hashtags."""
    out, last = [], 0
    for m in _HASHTAG.finditer(text):
        out.append(_RESERVED.sub(r"\\\1", text[last:m.start()]))
        out.append("{hashtag|\\#|" + m.group(1) + "}")
        last = m.end()
    out.append(_RESERVED.sub(r"\\\1", text[last:]))
    return "".join(out)


def candidate_versions(today: datetime.date | None = None) -> list[str]:
    """The API versions (YYYYMM) to try, best first: the one set in the settings, then this month and each month back."""
    today = today or datetime.date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(VERSION_MONTHS_BACK):
        months.append(f"{y}{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    configured = get_settings().linkedin_api_version.strip()
    return ([configured] if configured else []) + [v for v in months if v != configured]


def _check(res: httpx.Response, what: str) -> httpx.Response:
    if res.status_code >= 400:
        detail = ""
        try:  # LinkedIn's own short error code and message describe the problem; the rest of the body isn't logged
            body = res.json()
            detail = f" ({body.get('code') or body.get('serviceErrorCode')}: {str(body.get('message', ''))[:160]})"
        except ValueError:
            pass
        print(f"LinkedIn {what} failed: HTTP {res.status_code}{detail}")
        raise ShareError("LinkedIn didn’t accept the post. Try again in a moment.", 502)
    return res


def finish(code: str, state: str, client: httpx.Client | None = None, sleep: Callable[[float], None] = time.sleep) -> str:
    """Exchange the code, post the learner's draft once, and return the address of the post on LinkedIn."""
    draft = take_draft(state)
    s = get_settings()
    own = client is None
    http = client or httpx.Client(timeout=TIMEOUT)
    try:
        token = _check(http.post(TOKEN_URL, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": s.linkedin_redirect_uri,
            "client_id": s.linkedin_client_id, "client_secret": s.linkedin_client_secret,
        }), "token exchange").json().get("access_token")
        if not token:
            raise ShareError("LinkedIn didn’t sign you in. Try again.", 502)
        headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}

        sub = _check(http.get(f"{API}/v2/userinfo", headers=headers), "userinfo").json().get("sub")
        if not sub:
            raise ShareError("LinkedIn didn’t say who you are. Try again.", 502)
        owner = f"urn:li:person:{sub}"

        # LinkedIn answers 426 to a version it has retired, so find the newest one it serves and use it for the rest
        for version in candidate_versions():
            headers["LinkedIn-Version"] = version
            res = http.post(f"{API}/rest/images?action=initializeUpload", headers=headers, json={"initializeUploadRequest": {"owner": owner}})
            if res.status_code != 426:
                break
        else:
            print("LinkedIn API: every recent version was refused (HTTP 426)")
            raise ShareError("LinkedIn changed its API and Jobee needs an update to post. Copy the text and post it yourself for now.", 502)
        init = _check(res, "image upload start").json()["value"]
        _check(http.put(init["uploadUrl"], headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
                        content=draft.image), "image upload")
        image_urn = init["image"]
        for _ in range(6):  # LinkedIn processes the image for a moment before it can be attached
            status = _check(http.get(f"{API}/rest/images/{quote(image_urn, safe='')}", headers=headers), "image check").json().get("status")
            if status == "AVAILABLE":
                break
            sleep(1)
        else:
            raise ShareError("LinkedIn is still processing the image. Try again in a moment.", 502)

        res = _check(http.post(f"{API}/rest/posts", headers=headers, json={
            "author": owner,
            "commentary": commentary(draft.text),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "content": {"media": {"id": image_urn, "altText": "Jobee roadmap completed"}},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }), "post")
        post_urn = res.headers.get("x-restli-id")
        return f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else "https://www.linkedin.com/feed/"
    except httpx.HTTPError as e:
        print(f"LinkedIn call failed: {type(e).__name__}")
        raise ShareError("Couldn’t reach LinkedIn. Try again in a moment.", 502) from None
    except (KeyError, ValueError, TypeError):  # an answer in a shape we don't know
        print("LinkedIn answered in an unexpected shape")
        raise ShareError("LinkedIn answered in a way we didn’t expect. Try again in a moment.", 502) from None
    finally:
        if own:
            http.close()
