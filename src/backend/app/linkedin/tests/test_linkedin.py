"""Posting to LinkedIn, against a fake LinkedIn: each call is checked, and nothing goes over the network."""
import base64
import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.linkedin import service
from app.main import app

client = TestClient(app, follow_redirects=False)
PNG = base64.b64encode(service.PNG_MAGIC + b"fake image bytes").decode()


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "linkedin_client_id", "client-id")
    monkeypatch.setattr(s, "linkedin_client_secret", "client-secret")
    monkeypatch.setattr(s, "linkedin_redirect_uri", "http://localhost:8000/linkedin/callback")
    monkeypatch.setattr(s, "linkedin_return_url", "http://localhost:5173/pathway")
    service._drafts.clear()


def fake_linkedin(calls: list, image_status=("AVAILABLE",), fail_at: str | None = None, serves: set[str] | None = None):
    statuses = iter(image_status)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append((request.method, path))
        if fail_at and fail_at in path:
            return httpx.Response(500, json={"message": "secret detail"})
        if path == "/oauth/v2/accessToken":
            return httpx.Response(200, json={"access_token": "tok"})
        assert request.headers.get("Authorization") == "Bearer tok"
        version = request.headers.get("LinkedIn-Version")
        if path.startswith("/rest/") and serves is not None and version not in serves:
            calls.append(("RETIRED", version))
            return httpx.Response(426, json={"status": 426, "code": "NONEXISTENT_VERSION", "message": f"Requested version {version} is not active"})
        if path == "/v2/userinfo":
            return httpx.Response(200, json={"sub": "abc123"})
        if path == "/rest/images" and request.url.params.get("action") == "initializeUpload":
            assert json.loads(request.content)["initializeUploadRequest"]["owner"] == "urn:li:person:abc123"
            return httpx.Response(200, json={"value": {"uploadUrl": "https://upload.linkedin.test/put/1", "image": "urn:li:image:IMG1"}})
        if request.method == "PUT":
            assert request.content.startswith(service.PNG_MAGIC)
            return httpx.Response(201)
        if path.startswith("/rest/images/"):
            return httpx.Response(200, json={"status": next(statuses)})
        if path == "/rest/posts":
            body = json.loads(request.content)
            calls.append(("BODY", body))
            return httpx.Response(201, headers={"x-restli-id": "urn:li:share:999"})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def draft(text="I just completed a Jobee learning roadmap. #Jobee") -> str:
    url = service.start(text, PNG)
    return parse_qs(urlparse(url).query)["state"][0]


def test_status_follows_the_keys(monkeypatch):
    assert client.get("/linkedin/status").json() == {"enabled": True}
    monkeypatch.setattr(get_settings(), "linkedin_client_secret", "")
    assert client.get("/linkedin/status").json() == {"enabled": False}


def test_start_returns_the_linkedin_sign_in_address_for_one_post_only():
    res = client.post("/linkedin/share", json={"text": "Hello", "image_base64": PNG})
    assert res.status_code == 200
    url = urlparse(res.json()["authorize_url"])
    q = parse_qs(url.query)
    assert url.netloc == "www.linkedin.com" and url.path == "/oauth/v2/authorization"
    assert q["client_id"] == ["client-id"] and q["redirect_uri"] == ["http://localhost:8000/linkedin/callback"]
    assert q["scope"] == ["openid profile w_member_social"] and len(q["state"][0]) > 20


@pytest.mark.parametrize("text,image,message", [
    ("   ", PNG, "Write something"),
    ("x" * 3001, PNG, "3,000"),
    ("ok", "not base64!!", "image"),
    ("ok", base64.b64encode(b"GIF89a....").decode(), "PNG"),
    ("ok", base64.b64encode(service.PNG_MAGIC + b"0" * (service.MAX_IMAGE_BYTES + 1)).decode(), "too large"),
])
def test_a_bad_draft_is_refused(text, image, message):
    res = client.post("/linkedin/share", json={"text": text, "image_base64": image})
    assert res.status_code == 422 and message in res.json()["detail"]


def test_it_is_refused_when_the_keys_are_missing(monkeypatch):
    monkeypatch.setattr(get_settings(), "linkedin_client_id", "")
    assert client.post("/linkedin/share", json={"text": "Hi", "image_base64": PNG}).status_code == 503


def test_the_whole_flow_posts_once_and_returns_the_post_address():
    calls: list = []
    url = service.finish("the-code", draft(), client=fake_linkedin(calls))
    assert url == "https://www.linkedin.com/feed/update/urn:li:share:999/"
    order = [c for c in calls if c[0] != "BODY"]
    assert [p for _, p in order] == ["/oauth/v2/accessToken", "/v2/userinfo", "/rest/images", "/put/1", "/rest/images/urn:li:image:IMG1", "/rest/posts"]
    body = next(c[1] for c in calls if c[0] == "BODY")
    assert body["author"] == "urn:li:person:abc123" and body["lifecycleState"] == "PUBLISHED"
    assert body["content"]["media"]["id"] == "urn:li:image:IMG1"
    assert body["commentary"] == "I just completed a Jobee learning roadmap. {hashtag|\\#|Jobee}"


def test_a_sign_in_works_once_only():
    state = draft()
    service.finish("c", state, client=fake_linkedin([]))
    with pytest.raises(service.ShareError, match="expired"):
        service.finish("c", state, client=fake_linkedin([]))


def test_an_unknown_or_old_state_is_refused(monkeypatch):
    with pytest.raises(service.ShareError, match="expired"):
        service.finish("c", "never-issued", client=fake_linkedin([]))
    state = draft()
    monkeypatch.setattr(service.time, "time", lambda: 10**10)  # far past the 15 minutes
    with pytest.raises(service.ShareError, match="expired"):
        service.finish("c", state, client=fake_linkedin([]))


def test_it_waits_for_the_image_to_be_ready_and_gives_up_if_it_never_is():
    sleeps: list = []
    service.finish("c", draft(), client=fake_linkedin([], image_status=("WAITING_UPLOAD", "PROCESSING", "AVAILABLE")), sleep=sleeps.append)
    assert sleeps == [1, 1]
    with pytest.raises(service.ShareError, match="still processing"):
        service.finish("c", draft(), client=fake_linkedin([], image_status=("PROCESSING",) * 6), sleep=lambda s: None)


@pytest.mark.parametrize("fail_at", ["accessToken", "userinfo", "initialize", "/rest/posts"])
def test_a_linkedin_error_gives_a_plain_message_and_leaks_nothing(fail_at):
    fail = "/rest/images" if fail_at == "initialize" else fail_at
    with pytest.raises(service.ShareError) as e:
        service.finish("c", draft(), client=fake_linkedin([], fail_at=fail))
    assert "secret detail" not in e.value.message and "tok" not in e.value.message


def test_commentary_escapes_linkedins_reserved_characters_and_makes_real_hashtags():
    assert service.commentary("Skills (36) | 5 * sections_") == "Skills \\(36\\) \\| 5 \\* sections\\_"
    assert service.commentary("#Jobee #Up-skilling") == "{hashtag|\\#|Jobee} {hashtag|\\#|Up}-skilling"
    assert service.commentary("a@b <c> [d] {e} ~f \\g") == "a\\@b \\<c\\> \\[d\\] \\{e\\} \\~f \\\\g"


def test_the_callback_returns_the_browser_to_the_app_with_the_result(monkeypatch):
    monkeypatch.setattr(service, "finish", lambda code, state: "https://www.linkedin.com/feed/update/urn:li:share:9/")
    res = client.get("/linkedin/callback", params={"code": "c", "state": "s"})
    assert res.status_code == 303
    q = parse_qs(urlparse(res.headers["location"]).query)
    assert res.headers["location"].startswith("http://localhost:5173/pathway?") and q["linkedin"] == ["posted"]
    assert q["post"] == ["https://www.linkedin.com/feed/update/urn:li:share:9/"]


def test_the_callback_handles_a_refusal_a_missing_code_and_a_failure(monkeypatch):
    q = lambda r: parse_qs(urlparse(r.headers["location"]).query)  # noqa: E731
    assert q(client.get("/linkedin/callback", params={"error": "user_cancelled_authorize"}))["linkedin"] == ["cancelled"]
    assert q(client.get("/linkedin/callback"))["linkedin"] == ["error"]

    def boom(code, state):
        raise service.ShareError("LinkedIn didn’t accept the post. Try again in a moment.", 502)

    monkeypatch.setattr(service, "finish", boom)
    out = q(client.get("/linkedin/callback", params={"code": "c", "state": "s"}))
    assert out["linkedin"] == ["error"] and "didn’t accept" in out["reason"][0]


def test_it_finds_a_version_linkedin_still_serves_and_uses_it_for_every_call(monkeypatch):
    import datetime

    monkeypatch.setattr(service.datetime, "date", type("D", (datetime.date,), {"today": classmethod(lambda cls: datetime.date(2026, 10, 31))}))
    assert service.candidate_versions()[:3] == ["202610", "202609", "202608"]
    calls: list = []
    service.finish("c", draft(), client=fake_linkedin(calls, serves={"202608"}))
    assert [v for kind, v in calls if kind == "RETIRED"] == ["202610", "202609"]  # tried newest first, then moved on
    assert any(p == "/rest/posts" for _, p in calls if isinstance(p, str))


def test_a_version_set_in_the_settings_is_tried_first(monkeypatch):
    monkeypatch.setattr(get_settings(), "linkedin_api_version", "202601")
    assert service.candidate_versions()[0] == "202601"


def test_when_every_version_is_refused_it_says_so_plainly():
    with pytest.raises(service.ShareError, match="needs an update"):
        service.finish("c", draft(), client=fake_linkedin([], serves=set()))


def test_the_year_rolls_over_in_the_version_list():
    import datetime

    assert service.candidate_versions(datetime.date(2026, 2, 10))[:4] == ["202602", "202601", "202512", "202511"]
