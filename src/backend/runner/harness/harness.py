"""Evaluation harness. Runs INSIDE the sandbox container, never in the API process.

Reads one JSON job from stdin:
    {"mode": "evaluate", "mission_id": str, "code": str}
    {"mode": "request",  "mission_id": str, "code": str, "request": {...}}
and writes one result line prefixed with RESULT_MARKER to stdout.
"""

import contextlib
import io
import json
import os
import signal
import sys
import time
import traceback
import warnings

# Library notices are noise for learners; warnings from their own code still show.
warnings.filterwarnings("ignore", module=r"(fastapi|starlette|httpx|pydantic|anyio)(\..*)?$")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from missions import MISSIONS, TestFailure  # noqa: E402

RESULT_MARKER = "@@FRONTIER_RESULT@@"
FILENAME = "mission.py"
OUTPUT_LIMIT = 8000
LOAD_TIMEOUT_S = 3
TEST_TIMEOUT_S = 2


class Timeout(Exception):
    pass


class NoApp(Exception):
    pass


def _alarm(_signum, _frame):
    raise Timeout()


signal.signal(signal.SIGALRM, _alarm)


@contextlib.contextmanager
def time_limit(seconds):
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def learner_line(tb):
    """Line number of the deepest traceback frame inside the learner's file."""
    line = None
    for frame in traceback.extract_tb(tb):
        if frame.filename == FILENAME:
            line = frame.lineno
    return line


def categorize(exc):
    if isinstance(exc, SyntaxError):
        return "syntax"
    if isinstance(exc, NameError):
        return "name"
    if isinstance(exc, TypeError):
        return "type"
    if isinstance(exc, Timeout):
        return "timeout"
    if isinstance(exc, MemoryError):
        return "resource_limit"
    return "runtime"


def explain_name_error(exc, message):
    """Beginner-friendly reasons for the most common NameErrors."""
    name = getattr(exc, "name", None)
    if not name:
        return message
    if name == "___":
        return "There is still a ___ blank to fill in. Replace it with a value."
    for literal in ("True", "False", "None"):
        if name.lower() == literal.lower():
            return f"Python doesn't know `{name}`. It is written `{literal}`, with a capital first letter."
    return (
        f"Python doesn't know anything called `{name}`. "
        f'If you meant the text {name}, put it in quotes: "{name}". '
        "Otherwise check the spelling."
    )


def describe(exc):
    if isinstance(exc, SyntaxError):
        msg = exc.msg
        if exc.text and "___" in exc.text:
            msg += " — there is still a ___ blank to fill in"
        return {"type": "SyntaxError", "message": msg, "line": exc.lineno, "category": "syntax"}
    if isinstance(exc, Timeout):
        return {"type": "Timeout", "message": "Your code took too long — is something looping forever?", "line": None, "category": "timeout"}
    message = str(exc) or exc.__class__.__name__
    if isinstance(exc, NameError):
        message = explain_name_error(exc, message)
    return {
        "type": exc.__class__.__name__,
        "message": message,
        "line": learner_line(exc.__traceback__),
        "category": categorize(exc),
    }


def load(code):
    """Execute the learner's module. Returns its namespace."""
    namespace = {"__name__": "mission"}
    compiled = compile(code, FILENAME, "exec")
    with time_limit(LOAD_TIMEOUT_S):
        exec(compiled, namespace)
    return namespace


def clip(text):
    return text if len(text) <= OUTPUT_LIMIT else text[:OUTPUT_LIMIT] + "\n… (output truncated)"


def evaluate(job, out):
    mission = MISSIONS[job["mission_id"]]
    started = time.monotonic()
    stdout, stderr = io.StringIO(), io.StringIO()
    result = {"status": "passed", "tests": [], "error": None}

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            ns = load(job["code"])
        except BaseException as exc:  # noqa: BLE001 — anything the learner raises is reported, not fatal
            err = describe(exc)
            result.update(status="timeout" if err["category"] == "timeout" else "error", error=err)
            ns = None

        for test in mission["tests"]:
            outcome = {"id": test.id, "name": test.name, "passed": False}
            if ns is None:
                where = f" on line {result['error']['line']}" if result["error"].get("line") else ""
                outcome["message"] = f"Skipped — fix the {result['error']['type']}{where} first (see above)."
                result["tests"].append(outcome)
                continue
            try:
                with time_limit(TEST_TIMEOUT_S):
                    test.fn(ns)
                outcome["passed"] = True
            except TestFailure as f:
                outcome.update(message=str(f), category=f.category)
            except BaseException as exc:  # noqa: BLE001
                err = describe(exc)
                where = f" (line {err['line']})" if err["line"] else ""
                outcome.update(message=f"{err['type']}{where}: {err['message']}", category=err["category"])
            result["tests"].append(outcome)

    if result["status"] == "passed" and not all(t["passed"] for t in result["tests"]):
        result["status"] = "failed"
    result.update(
        stdout=clip(stdout.getvalue()),
        stderr=clip(stderr.getvalue()),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    out(result)


def run_request(job, out):
    started = time.monotonic()
    logs = io.StringIO()
    req = job["request"]
    result = {"response": None, "error": None}

    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        try:
            ns = load(job["code"])
            app = ns.get("app")
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            if not isinstance(app, FastAPI):
                raise NoApp("No FastAPI app found. Your file needs `app = FastAPI()`.")
            client = TestClient(app, raise_server_exceptions=True)
            kwargs = {"params": req.get("query") or {}, "headers": req.get("headers") or {}}
            if req["method"] not in ("GET", "DELETE") and req.get("body") is not None:
                kwargs["json"] = req["body"]
            with time_limit(TEST_TIMEOUT_S):
                resp = client.request(req["method"], req["path"], **kwargs)
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            result["response"] = {
                "status_code": resp.status_code,
                "headers": {k: v for k, v in resp.headers.items() if k in ("content-type", "content-length")},
                "body": body,
            }
        except BaseException as exc:  # noqa: BLE001
            result["error"] = describe(exc)
            # A crash inside a route is what a real client sees as a 500.
            if not isinstance(exc, (SyntaxError, NoApp, Timeout)) and learner_line(exc.__traceback__):
                result["response"] = {
                    "status_code": 500,
                    "headers": {"content-type": "text/plain"},
                    "body": "Internal Server Error",
                }
            traceback.print_exc(file=logs)

    result.update(logs=clip(logs.getvalue()), duration_ms=int((time.monotonic() - started) * 1000))
    out(result)


def main():
    real_stdout = sys.stdout

    def out(payload):
        real_stdout.write(RESULT_MARKER + json.dumps(payload, default=str) + "\n")
        real_stdout.flush()

    job = json.loads(sys.stdin.read())
    if job.get("mission_id") not in MISSIONS:
        out({"fatal": f"Unknown mission {job.get('mission_id')!r}"})
        return
    if job["mode"] == "evaluate":
        evaluate(job, out)
    elif job["mode"] == "request":
        run_request(job, out)
    else:
        out({"fatal": f"Unknown mode {job['mode']!r}"})


if __name__ == "__main__":
    main()
