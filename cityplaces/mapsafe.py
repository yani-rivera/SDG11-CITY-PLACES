"""Security pieces of the map page: pinned library with integrity hashes, URL checks,
safe JSON for embedding, and the Content-Security-Policy."""
import base64
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

# MapLibre GL JS, pinned. The integrity hashes make the browser refuse a changed file.
# To upgrade: change the version and recompute both hashes, e.g.
#   curl -sL https://unpkg.com/maplibre-gl@<v>/dist/maplibre-gl.js | openssl dgst -sha384 -binary | base64
MAPLIBRE = {
    "version": "4.7.1",
    "js": "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js",
    "js_sri": "sha384-SYKAG6cglRMN0RVvhNeBY0r3FYKNOJtznwA0v7B5Vp9tr31xAHsZC0DqkQ/pZDmj",
    "css": "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css",
    "css_sri": "sha384-MinO0mNliZ3vwppuPOUnGa+iq619pfMhLVUXfC4LHwSCvF9H+6P/KO4Q7qBOYV5V",
}


def safe_url(url: str, https_only: bool = False) -> str | None:
    """The URL if it is plain http(s) (https only when asked), else None."""
    try:
        parts = urlsplit(str(url).strip())
    except ValueError:
        return None
    allowed = ("https",) if https_only else ("http", "https")
    if parts.scheme not in allowed or not parts.netloc or any(c in str(url) for c in "\"'<> \n\r\t"):
        return None
    return str(url).strip()


def origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def _clean(obj):
    """NaN/inf -> None: JSON.parse rejects them."""
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    return obj


def to_json(obj) -> str:
    """Strict JSON. Also safe inside <script type="application/json">: place names are
    untrusted text, so '<' is escaped and a name can never close the script block."""
    s = json.dumps(_clean(obj), separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return s.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def inline_script_hashes(html: str) -> list[str]:
    """CSP hashes of the inline <script> blocks that run (JSON data blocks do not run)."""
    out = []
    for m in re.finditer(r"<script>(.*?)</script>", html, flags=re.S):
        digest = base64.b64encode(hashlib.sha256(m.group(1).encode("utf-8")).digest()).decode()
        out.append(f"'sha256-{digest}'")
    return out


def csp(html: str, map_origins: list[str]) -> str:
    """Content-Security-Policy for the page. Scripts: only the pinned MapLibre and the page's
    own inline script (by hash). Network: only this site and the basemap servers."""
    lib = origin(MAPLIBRE["js"])
    net = " ".join(sorted(set(map_origins)))
    return "; ".join([
        "default-src 'none'",
        f"script-src {lib} " + " ".join(inline_script_hashes(html)),
        f"style-src {lib} 'unsafe-inline'",          # MapLibre sets inline styles on its elements
        f"img-src 'self' data: blob: {net}",
        f"font-src {net}",
        f"connect-src 'self' {net}",
        "worker-src blob:",
        "child-src blob:",
        "base-uri 'none'",
        "form-action 'none'",
    ])
