"""Resize and cache remote bike thumbnails (WebP) for list views."""

from __future__ import annotations

import hashlib
from io import BytesIO

import requests
from flask import Blueprint, Response, abort, current_app, request
from PIL import Image

from urllib.parse import urlparse

from app.extensions import cache
from app.utils.bike_images import bike_image_host_allowed

bp = Blueprint("images", __name__)

_MAX_UPSTREAM_BYTES = 6_000_000
_MAX_EDGE_PX = 280
_WEBP_QUALITY = 82
_CACHE_SECONDS = 86400


def _fetch_resize_webp(src_url: str) -> bytes:
    resp = requests.get(
        src_url,
        timeout=14,
        headers={"User-Agent": "RidealThumbProxy/1.0"},
    )
    resp.raise_for_status()
    if len(resp.content) > _MAX_UPSTREAM_BYTES:
        raise ValueError("upstream image too large")
    im = Image.open(BytesIO(resp.content))
    if im.mode not in ("RGB", "RGBA"):
        if im.mode == "P" and "transparency" in im.info:
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
    im.thumbnail((_MAX_EDGE_PX, _MAX_EDGE_PX), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="WEBP", quality=_WEBP_QUALITY, method=4)
    return buf.getvalue()


@bp.route("/i/bike-thumb")
def bike_thumb():
    src = request.args.get("u", type=str)
    if not src:
        abort(404)
    parsed = urlparse(src)
    if parsed.scheme != "https" or not parsed.netloc:
        abort(404)
    if not bike_image_host_allowed(parsed.netloc):
        abort(404)

    key = "bike_thumb:" + hashlib.sha256(src.encode("utf-8", errors="surrogateescape")).hexdigest()
    data = cache.get(key)
    if data is None:
        try:
            data = _fetch_resize_webp(src)
        except Exception:
            current_app.logger.exception("bike_thumb fetch failed: %s", src[:120])
            abort(502)
        cache.set(key, data, timeout=_CACHE_SECONDS)

    return Response(
        data,
        mimetype="image/webp",
        headers={"Cache-Control": "public, max-age=604800"},
    )
