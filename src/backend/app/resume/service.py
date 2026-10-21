import time
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import get_settings
from app.resume import gateway, openjev
from app.resume.vocab import TOP_N

MAX_BYTES = 10 * 1024 * 1024  # reject uploads over 10 MB
MAX_PAGES = 10  # a resume is a few pages; ignore the rest
MAX_TEXT_CHARS = 15000  # resume text sent to the model; the rest is cut


class ResumeError(Exception):
    """A problem with the uploaded file; carries the HTTP status to answer with."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def extract_pdf_text(data: bytes) -> dict:
    """Read a PDF's text layer and return the text with page and size details.

    Checks the file's first bytes (not its name), the size, that it is not password-protected, and
    that it can be parsed. Only the first MAX_PAGES pages are read. Raises ResumeError otherwise.
    """
    if not data:
        raise ResumeError(400, "The file is empty.")
    if len(data) > MAX_BYTES:
        raise ResumeError(413, f"The file is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if not data.lstrip().startswith(b"%PDF-"):
        raise ResumeError(400, "Only PDF files are supported.")

    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ResumeError(422, "The PDF is password-protected. Remove the password and upload it again.")
        page_count = len(reader.pages)
        pages = reader.pages[:MAX_PAGES]
        text = "\n\n".join((page.extract_text() or "").strip() for page in pages).strip()
    except ResumeError:
        raise
    except (PdfReadError, ValueError, KeyError, OSError):
        raise ResumeError(422, "The PDF could not be read. It may be damaged.")

    return {
        "page_count": page_count,
        "pages_read": len(pages),
        "char_count": len(text),
        "text": text,
    }


def extract_skills(text: str, source: str = "auto") -> dict:
    """Get the resume's top skills from OpenJev or the gateway LLM, and time it.

    Both engines get the same candidate skill list and return the same shape.
    source: "auto" uses OpenJev when OPENJEV_URL is set and falls back to the LLM if it fails;
    "openjev" or "llm" use only that engine with no fallback, so a failure shows up as an error
    (this is what makes the two comparable). Returns {"skills", "top_skills", "error", "engine": {...}}, where skills are
    [{"name", "score"}] strongest first and top_skills is the first TOP_N of them. Never raises.
    """
    start = time.perf_counter()
    result = _extract(text, source)
    result["engine"]["seconds"] = round(time.perf_counter() - start, 2)
    return result


def _extract(text: str, source: str) -> dict:
    """The work behind extract_skills: pick the engine, call it, label the result."""
    settings = get_settings()
    model = settings.resume_model or settings.openrouter_model
    none = {"source": None, "model": None, "candidates": None, "seconds": None}

    def failed(message: str) -> dict:
        return {"skills": None, "top_skills": None, "error": message, "engine": dict(none)}

    text = text[:MAX_TEXT_CHARS]
    if not text.strip():
        return failed("No text was found in the PDF (it may be a scan), so no skills were extracted.")
    if source == "openjev" and not settings.openjev_url:
        return failed("OPENJEV_URL is not set, so OpenJev can't be used.")
    if source in ("auto", "openjev") and settings.openjev_url:
        try:
            found = openjev.score_resume(text)
            return {"skills": found["skills"], "top_skills": found["skills"][:TOP_N], "error": None,
                    "engine": {**none, "source": "openjev", "model": "openjev", "candidates": found["candidates"]}}
        except Exception as e:  # server down, bad token, timeout, unexpected reply
            if source == "openjev":
                return failed(f"OpenJev failed: {type(e).__name__}.")
            print(f"OpenJev failed ({type(e).__name__}: {e}); falling back to the LLM")
    try:
        found = gateway.score_resume(text)
        return {"skills": found["skills"], "top_skills": found["skills"][:TOP_N], "error": None,
                "engine": {**none, "source": "llm", "model": model, "candidates": found["candidates"]}}
    except ValueError:
        return failed("The model's answer could not be read as JSON. Try again.")
    except Exception as e:  # network, auth, timeout, unknown model...
        return failed(f"The skills step failed: {type(e).__name__}.")
