import json
import queue
import threading
from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.resume import service
from app.resume.schemas import ResumeOut

router = APIRouter(prefix="/resume", tags=["resume"])

SOURCE_HELP = (
    "Which engine reads the skills. auto = OpenJev with fallback to the gateway LLM; openjev or llm = only that one, "
    "no fallback ('openai' and 'grafilab' mean the gateway LLM)"
)
Source = Literal["auto", "openjev", "llm", "openai", "grafilab"]
KEEPALIVE_SECONDS = 10  # a quiet connection (OpenJev answers in one go) is not closed by proxies in between


def _read_pdf(file: UploadFile) -> dict:
    data = file.file.read(service.MAX_BYTES + 1)  # one byte over the limit is enough to reject it
    try:
        return service.extract_pdf_text(data)
    except service.ResumeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


def _resume_out(file: UploadFile, pdf: dict, skills: dict) -> ResumeOut:
    return ResumeOut(
        filename=file.filename,
        page_count=pdf["page_count"],
        char_count=pdf["char_count"],
        top_skills=skills["top_skills"],
        skills=skills["skills"],
        error=skills["error"],
        engine=skills["engine"],
    )


@router.post("", response_model=ResumeOut)
def read_resume(
    file: UploadFile = File(description="The resume as a PDF (max 10 MB)"),
    source: Source = Query("auto", description=SOURCE_HELP),
):
    """Read a resume PDF (no login needed). Nothing is saved, so resume_id is null; returns the skills found with a score each, and the top 5."""
    pdf = _read_pdf(file)
    engine = "llm" if source in ("openai", "grafilab") else source
    return _resume_out(file, pdf, service.extract_skills(pdf["text"], engine))


@router.post("/stream")
def read_resume_stream(
    file: UploadFile = File(description="The resume as a PDF (max 10 MB)"),
    source: Source = Query("auto", description=SOURCE_HELP),
):
    """Same as POST /resume, but answers as server-sent events so a page can show progress during the wait.

    A bad file is rejected up front with the same status codes as POST /resume. Otherwise each event is a line
    `data: {json}` with a `type`: `read` (page_count, char_count, expected_seconds), `candidates` (count), `engine` (source),
    `thinking` (words so far; about once a second while the gateway LLM reasons), `skill` (name, score; one per skill
    as the gateway LLM writes its answer) and finally `result`,
    which carries the same fields as the POST /resume response.
    """
    pdf = _read_pdf(file)
    engine = "llm" if source in ("openai", "grafilab") else source
    events: queue.Queue = queue.Queue()
    done = object()

    def work():
        try:
            events.put(("result", service.extract_skills(pdf["text"], engine, on_event=events.put)))
        except Exception as e:  # extract_skills doesn't raise; this keeps the stream from hanging if it ever does
            events.put(("failed", f"{type(e).__name__}"))
        events.put(done)

    def sse(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    def stream():
        yield sse({"type": "read", "page_count": pdf["page_count"], "char_count": pdf["char_count"], "expected_seconds": service.expected_seconds()})
        threading.Thread(target=work, daemon=True).start()
        while True:
            try:
                item = events.get(timeout=KEEPALIVE_SECONDS)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if item is done:
                return
            if isinstance(item, tuple):
                kind, payload = item
                if kind == "failed":
                    yield sse({"type": "failed", "message": "Something went wrong reading your resume."})
                else:
                    yield sse({"type": "result", **_resume_out(file, pdf, payload).model_dump()})
            else:
                yield sse(item)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
