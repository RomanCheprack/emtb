"""Helpers for bike catalogue images (list thumbnails, proxy allow-list)."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import url_for

# Host suffixes for retailer product images we may fetch and resize server-side.
# Keep in sync with scraper sources; unknown hosts still use the original URL.
_ALLOWED_HOST_SUFFIXES: frozenset[str] = frozenset(
    {
        "rosen-meents.co.il",
        "recycles.co.il",
        "giant-bike.co.il",
        "ctc.co.il",
        "pedalim.co.il",
        "moto-ofan.co.il",
        "motosport-bicycle.co.il",
        "matzman-merutz.co.il",
        "rudy-extreme.co.il",
        "rl-bikes.co.il",
        "cobra-bordo.co.il",
        "twoo-bikes.co.il",
    }
)


def bike_image_host_allowed(netloc: str) -> bool:
    """Return True if netloc may be fetched by the thumbnail proxy."""
    h = (netloc or "").lower().split(":")[0]
    if h.startswith("www."):
        h = h[4:]
    for suffix in _ALLOWED_HOST_SUFFIXES:
        if h == suffix or h.endswith("." + suffix):
            return True
    return False


def bike_list_thumb_url(source_url: str | None) -> str | None:
    """URL for the bike row thumbnail: proxied WebP when allowed, else original.

    Falls back to the raw ``image_url`` for http, unknown hosts, or parse errors
    so we never break images when the proxy cannot apply.
    """
    if source_url is None:
        return None
    s = str(source_url).strip()
    if not s:
        return None
    try:
        parsed = urlparse(s)
        if parsed.scheme != "https" or not parsed.netloc:
            return s
        if not bike_image_host_allowed(parsed.netloc):
            return s
        return url_for("images.bike_thumb", u=s)
    except Exception:
        return s
