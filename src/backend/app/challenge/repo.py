"""Reads a public GitHub repository for judging: its file tree, plus the files that best show what was built.

Only github.com repository URLs are accepted, so the backend never fetches an address the user chose. Two GitHub API
calls (the repo, for its default branch, and its recursive tree), then file contents from raw.githubusercontent.com,
which does not count against the API's rate limit (60 an hour without GITHUB_TOKEN, 5,000 with it).
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx

from app.config import get_settings

MAX_FILES = 30
MAX_FILE_CHARS = 8_000  # a longer file is cut, with a marker
MAX_TOTAL_CHARS = 100_000  # ~25-30k tokens of code for the judge
MAX_TREE_PATHS = 400
MAX_BLOB_BYTES = 300_000  # bigger files are data or generated, not worth reading

URL = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:/(?:tree|blob)/[^?#]*)?/?(?:[?#].*)?$")

SKIP_DIRS = {
    "node_modules", "dist", "build", "out", "target", "vendor", "bin", "obj", "coverage", "__pycache__", "site-packages",
    ".git", ".github", ".venv", "venv", "env", ".next", ".nuxt", ".svelte-kit", ".idea", ".vscode", ".pytest_cache",
    ".mypy_cache", ".ipynb_checkpoints", ".gradle",
}
SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "pipfile.lock", "composer.lock",
    "cargo.lock", "go.sum", "gemfile.lock", ".ds_store",
}
CODE_EXTS = {
    ".py", ".ipynb", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss",
    ".sass", ".less", ".java", ".kt", ".scala", ".go", ".rs", ".rb", ".php", ".cs", ".c", ".h", ".cpp", ".hpp", ".swift",
    ".dart", ".sql", ".r", ".rmd", ".jl", ".m", ".sh", ".ps1", ".yml", ".yaml", ".toml", ".json", ".xml", ".md",
    ".graphql", ".prisma", ".tf",
}
# Always read, when present (lowercase file names): what the project is and what it is built with.
KEY_FILES = {
    "package.json", "requirements.txt", "pyproject.toml", "pipfile", "setup.py", "environment.yml", "pom.xml",
    "build.gradle", "build.gradle.kts", "go.mod", "cargo.toml", "composer.json", "gemfile", "dockerfile",
    "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "compose.yml", "schema.prisma", ".env.example",
}
ENTRY_STEMS = {"main", "app", "index", "server", "routes", "router", "api", "models", "model", "views", "schema", "db", "database", "train", "analysis"}
# Words in a stack skill's O*NET name -> the file extensions that show it being used.
STACK_EXTS = {
    "python": {".py", ".ipynb"}, "django": {".py"}, "flask": {".py"}, "pandas": {".py", ".ipynb"}, "numpy": {".py", ".ipynb"},
    "scikit": {".py", ".ipynb"}, "tensorflow": {".py", ".ipynb"}, "pytorch": {".py", ".ipynb"}, "jupyter": {".ipynb"},
    "javascript": {".js", ".jsx", ".mjs"}, "jquery": {".js"}, "node": {".js", ".ts", ".mjs"}, "typescript": {".ts", ".tsx"},
    "react": {".jsx", ".tsx", ".js"}, "vue": {".vue"}, "angular": {".ts", ".html"}, "html": {".html", ".htm"},
    "css": {".css", ".scss", ".sass", ".less"}, "bootstrap": {".html", ".css"}, "sql": {".sql"}, "postgresql": {".sql"},
    "mysql": {".sql"}, "oracle": {".sql"}, "java": {".java"}, "spring": {".java"}, "kotlin": {".kt"}, "scala": {".scala"},
    "c#": {".cs"}, "c++": {".cpp", ".hpp", ".h"}, "php": {".php"}, "ruby": {".rb"}, "swift": {".swift"}, "r": {".r", ".rmd"},
    "matlab": {".m"}, "bash": {".sh"}, "shell": {".sh"}, "powershell": {".ps1"}, "json": {".json"}, "xml": {".xml"},
    "graphql": {".graphql"}, "terraform": {".tf"}, "docker": {".yml", ".yaml"},
}


class RepoError(Exception):
    """The repo could not be read; message can be shown to the user as is."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class Snapshot:
    url: str
    tree: list[str]  # every file path, cut to MAX_TREE_PATHS
    tree_total: int
    files: list[tuple[str, str]] = field(default_factory=list)  # (path, text) in the order the judge reads them


def parse_url(url: str) -> tuple[str, str, str]:
    """(owner, repo, canonical https://github.com/owner/repo) or RepoError 422."""
    m = URL.match(url.strip())
    if not m:
        raise RepoError(422, "Paste the link to a GitHub repository, like https://github.com/you/your-project.")
    owner, repo = m.group(1), m.group(2)
    return owner, repo, f"https://github.com/{owner}/{repo}"


def _skipped(path: str) -> bool:
    p = PurePosixPath(path)
    name = p.name.lower()
    return any(part.lower() in SKIP_DIRS for part in p.parts[:-1]) or name in SKIP_FILES or ".min." in name or p.suffix.lower() == ".map"


def stack_exts(stack_skills: list[str]) -> set[str]:
    """File extensions that show the stack's skills, from the words in their names."""
    out: set[str] = set()
    for name in stack_skills:
        for word in re.findall(r"[a-z+#]+", name.lower()):
            out |= STACK_EXTS.get(word, set())
    return out


def select(blobs: list[tuple[str, int]], stack_skills: list[str]) -> list[str]:
    """Which files to read, best first: READMEs and manifests, then code ranked by how well it shows the stack,
    favouring entry points and shallow paths. blobs is (path, size)."""
    wanted_exts = stack_exts(stack_skills)
    key, ranked = [], []
    for path, size in blobs:
        if _skipped(path) or size > MAX_BLOB_BYTES:
            continue
        p = PurePosixPath(path)
        name, ext, depth = p.name.lower(), p.suffix.lower(), len(p.parts) - 1
        if name.startswith("readme") and depth <= 1:
            key.append((0 if depth == 0 else 1, depth, path))
        elif name in KEY_FILES and depth <= 2:
            key.append((2, depth, path))
        elif ext in CODE_EXTS and ext != ".md" and (ext != ".json" or depth == 0):
            score = (3 if ext in wanted_exts else 0) + (2 if p.stem.lower() in ENTRY_STEMS else 0) - 0.5 * depth
            score -= 1.5 if re.search(r"(^|/)(tests?|__tests__|spec)(/|$)|\.(test|spec)\.", path.lower()) else 0
            score -= 1 if ext in {".json", ".yml", ".yaml", ".toml", ".xml"} else 0
            ranked.append((-score, path))
    return [p for *_, p in sorted(key)] + [p for _, p in sorted(ranked)][: max(0, MAX_FILES - len(key))]


def _notebook(text: str) -> str:
    """A Jupyter notebook's cells as plain source, without outputs (which are mostly images and big tables)."""
    try:
        cells = json.loads(text).get("cells") or []
    except (ValueError, AttributeError):
        return text
    parts = []
    for c in cells:
        src = "".join(c.get("source") or []) if isinstance(c.get("source"), list) else str(c.get("source") or "")
        if src.strip():
            parts.append(f"# [{c.get('cell_type', 'cell')}]\n{src}")
    return "\n\n".join(parts)


def _get(client: httpx.Client, url: str) -> httpx.Response:
    try:
        return client.get(url)
    except httpx.HTTPError as e:
        raise RepoError(502, "GitHub didn’t answer. Try again in a moment.") from e


def fetch(url: str, stack_skills: list[str]) -> Snapshot:
    """The repo's tree and the files the judge should read, within the size caps."""
    owner, repo, canonical = parse_url(url)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "jobee-bonus-quests"}
    if token := get_settings().github_token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(headers=headers, timeout=20, follow_redirects=True) as client:
        meta = _get(client, f"https://api.github.com/repos/{owner}/{repo}")
        if meta.status_code == 404:
            raise RepoError(404, "We couldn’t find that repo. Check the link, and make sure the repo is public.")
        if meta.status_code in (403, 429):
            raise RepoError(503, "GitHub is limiting how often we can read repos right now. Try again in a few minutes.")
        if meta.status_code != 200:
            raise RepoError(502, "GitHub didn’t answer properly. Try again in a moment.")
        branch = meta.json().get("default_branch") or "main"

        tree = _get(client, f"https://api.github.com/repos/{owner}/{repo}/git/trees/{quote(branch, safe='')}?recursive=1")
        if tree.status_code in (404, 409):
            raise RepoError(422, "That repo is empty. Push your code first, then submit it.")
        if tree.status_code != 200:
            raise RepoError(502, "GitHub didn’t answer properly. Try again in a moment.")
        blobs = [(t["path"], t.get("size") or 0) for t in tree.json().get("tree") or [] if t.get("type") == "blob"]
        if not blobs:
            raise RepoError(422, "That repo is empty. Push your code first, then submit it.")

        paths = [p for p, _ in blobs if not _skipped(p)]
        snap = Snapshot(url=canonical, tree=paths[:MAX_TREE_PATHS], tree_total=len(paths))
        chosen = select(blobs, stack_skills)

        def raw(path: str) -> str | None:
            r = client.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{quote(branch, safe='')}/{quote(path)}")
            if r.status_code != 200 or b"\x00" in r.content[:1024]:
                return None  # missing, or binary
            return r.content.decode("utf-8", errors="replace")

        with ThreadPoolExecutor(max_workers=8) as pool:
            texts = list(pool.map(lambda p: _safe(raw, p), chosen))

    total = 0
    for path, text in zip(chosen, texts):
        if text is None:
            continue
        if path.lower().endswith(".ipynb"):
            text = _notebook(text)
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n… (rest of file not shown)"
        if total + len(text) > MAX_TOTAL_CHARS:
            break
        snap.files.append((path, text))
        total += len(text)
    if not snap.files:
        raise RepoError(422, "We couldn’t find any code to read in that repo.")
    return snap


def _safe(fn, path: str):
    """fn(path), or None if the request failed: one unreadable file shouldn't sink the submission."""
    try:
        return fn(path)
    except httpx.HTTPError:
        return None
