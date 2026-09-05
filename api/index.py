import sys
from pathlib import Path

# Keep the Vercel function as an adapter; domain routes remain in backend/app.
backend_root = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_root))

from app.main import app as _app


async def app(scope, receive, send):
    if scope["type"] == "http" and scope.get("path", "").startswith("/api"):
        scope = dict(scope)
        scope["path"] = scope["path"][4:] or "/"
        scope["raw_path"] = scope.get("raw_path", b"")[4:] or b"/"
    await _app(scope, receive, send)
