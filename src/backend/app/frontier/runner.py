"""Runs learner code in a throwaway Docker container.

The API process never imports or executes learner code. Each job is a fresh
`docker run` with no network, a read-only root filesystem, a non-root user,
dropped capabilities and memory/CPU/process limits. The job goes in on stdin and
one JSON result line comes back on stdout.
"""

import json
import shutil
import subprocess
import uuid
from pathlib import Path

IMAGE = "frontier-runner:latest"
RUNNER_DIR = Path(__file__).resolve().parents[2] / "runner"
RESULT_MARKER = "@@FRONTIER_RESULT@@"
MAX_CODE_CHARS = 20_000
MAX_OUTPUT_BYTES = 256_000
WALL_TIMEOUT_S = 15

KNOWN_MISSIONS = {
    "w1-satchel",
    "w1-rocks",
    "w1-ledger",
    "w1-signal",
    "w1-first-route",
    "w1-copper-rights",
}


class RunnerUnavailable(Exception):
    """Docker or the runner image is missing. Never fall back to running code locally."""


class RunnerFailure(Exception):
    """The sandbox ran but did not produce a usable result."""


def docker_cmd(name: str) -> list[str]:
    return [
        "docker", "run", "--rm", "-i",
        "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--user", "10001:10001",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "256m",
        "--memory-swap", "256m",
        "--cpus", "1",
        "--pids-limit", "64",
        "--ulimit", "nofile=64:64",
        "--ulimit", "fsize=1048576:1048576",
        IMAGE,
    ]


def health() -> dict:
    """Raises RunnerUnavailable with an actionable message if code can't run safely."""
    if not shutil.which("docker"):
        raise RunnerUnavailable("Docker isn't installed or not on PATH. Install Docker Desktop to run learner code.")
    try:
        info = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=8)
    except subprocess.TimeoutExpired:
        raise RunnerUnavailable("Docker didn't respond. Is Docker Desktop still starting?")
    if info.returncode != 0:
        raise RunnerUnavailable("The Docker daemon isn't running. Start Docker Desktop.")
    image = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, text=True, timeout=8)
    if image.returncode != 0:
        raise RunnerUnavailable(f"Runner image missing. Build it with: docker build -t {IMAGE} src/backend/runner")
    return {"status": "ok", "isolation": "docker", "docker_version": info.stdout.strip()}


def run_job(job: dict) -> dict:
    code = job.get("code", "")
    if len(code) > MAX_CODE_CHARS:
        raise RunnerFailure(f"Code is too long ({len(code)} characters, limit {MAX_CODE_CHARS}).")
    if job.get("mission_id") not in KNOWN_MISSIONS:
        raise RunnerFailure(f"Unknown mission {job.get('mission_id')!r}.")

    name = f"frontier-run-{uuid.uuid4().hex[:12]}"
    try:
        proc = subprocess.run(
            docker_cmd(name),
            input=json.dumps(job).encode(),
            capture_output=True,
            timeout=WALL_TIMEOUT_S,
        )
    except FileNotFoundError:
        raise RunnerUnavailable("Docker isn't installed or not on PATH.")
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return {"timeout": True}

    stdout = proc.stdout[:MAX_OUTPUT_BYTES].decode(errors="replace")
    stderr = proc.stderr[:4000].decode(errors="replace")
    if proc.returncode == 125 or "Unable to find image" in stderr:
        raise RunnerUnavailable(f"Couldn't start the sandbox: {stderr.strip() or 'docker run failed'}")
    if proc.returncode == 137:
        return {"oom": True}

    # The harness prints exactly one marked line; take the last in case learner output imitates it.
    lines = [ln for ln in stdout.splitlines() if ln.startswith(RESULT_MARKER)]
    if not lines:
        raise RunnerFailure(f"The sandbox exited without a result (exit {proc.returncode}). {stderr.strip()[:500]}")
    result = json.loads(lines[-1][len(RESULT_MARKER):])
    if "fatal" in result:
        raise RunnerFailure(result["fatal"])
    return result
