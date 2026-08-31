"""
Minimal TOTP (RFC 6238) implementation for the Main Administrator's
2FA, using only the Python standard library — no third-party
dependency (e.g. pyotp) is required. Compatible with Google
Authenticator, Microsoft Authenticator, and any other standard TOTP
app: 30-second step, 6 digits, SHA1, the same defaults those apps
assume.

Nothing here stores or logs a generated/entered code — see
accounts.services for how this is used, and accounts.models.User.
totp_secret for why the *secret* (unlike a code) has to be stored
in the clear to be usable at all.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def generate_totp_secret():
    """A fresh random base32 secret, suitable for encoding into a QR code / manual-entry string."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _hotp(secret_base32, counter):
    key = base64.b32decode(secret_base32.upper() + "=" * ((8 - len(secret_base32) % 8) % 8))
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return truncated % (10**TOTP_DIGITS)


def generate_totp(secret_base32, *, at_time=None):
    """The current 6-digit code for this secret, as a zero-padded string."""
    at_time = at_time if at_time is not None else time.time()
    counter = int(at_time // TOTP_STEP_SECONDS)
    return f"{_hotp(secret_base32, counter):0{TOTP_DIGITS}d}"


def verify_totp(secret_base32, code, *, at_time=None, window=1):
    """
    True if `code` matches the secret for the current time step, or up
    to `window` steps before/after — a small tolerance for clock drift
    between this server and the user's phone, standard practice for
    TOTP. Comparison is constant-time to avoid leaking timing
    information about which digits matched.
    """
    if not code or not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    at_time = at_time if at_time is not None else time.time()
    counter = int(at_time // TOTP_STEP_SECONDS)
    for offset in range(-window, window + 1):
        expected = f"{_hotp(secret_base32, counter + offset):0{TOTP_DIGITS}d}"
        if hmac.compare_digest(expected, code):
            return True
    return False


def generate_backup_codes(count=10):
    """Plain-text codes to show the user ONCE at setup time — the caller is responsible for hashing before storing (see accounts.services.setup_totp)."""
    return [f"{secrets.randbelow(1_000_000):06d}-{secrets.randbelow(1_000_000):06d}" for _ in range(count)]
