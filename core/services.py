"""Project-wide business logic shared across apps."""

import logging

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_address(address):
    """
    Best-effort address -> (latitude, longitude) lookup using
    OpenStreetMap's free Nominatim service. No API key required.

    Returns (None, None) on ANY failure — bad address, network error,
    timeout, service unavailable, or an address too vague to resolve.
    This is explicitly best-effort: it must never raise, and callers
    (e.g. checkout) must not depend on it succeeding. Nominatim's
    usage policy caps this at ~1 request/second and requires an
    identifying User-Agent, both of which matter if this is ever
    called somewhere higher-volume than one lookup per checkout.
    """
    if not address or not address.strip():
        return None, None

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "LolairesKitchen/1.0 (restaurant order delivery)"},
            timeout=5,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Geocoding failed for address %r: %s", address, exc)
        return None, None

    if not results:
        return None, None

    try:
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Unexpected geocoding response for address %r: %s", address, exc)
        return None, None
