import msal
import threading

# ── Microsoft Entra Configuration ──────────────────────────────────────────────
CLIENT_ID = "e20f04d6-7a3d-4ea4-8abb-17092649496b"
TENANT_ID = "dafe49bc-5ac3-4310-97b4-3e44a28cbf18"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Chat.ReadWrite", "ChatMessage.Send", "User.Read"]

# ── Global state ───────────────────────────────────────────────────────────────
_app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
_flow = None
_access_token: str | None = None
_auth_status: str = "not_started"   # not_started | pending | success | failed
_auth_lock = threading.Lock()


def initiate_device_flow() -> dict:
    """Start the MSAL device flow and return user_code + verification_uri."""
    global _flow, _auth_status, _access_token

    with _auth_lock:
        _access_token = None
        _auth_status = "pending"
        _flow = _app.initiate_device_flow(scopes=SCOPES)

    if "user_code" not in _flow:
        _auth_status = "failed"
        raise RuntimeError("Device flow initiation failed: " + str(_flow.get("error_description", "")))

    return {
        "user_code": _flow["user_code"],
        "verification_uri": _flow["verification_uri"],
        "message": _flow["message"],
    }


def _poll_for_token() -> None:
    """Background thread: blocks until the user completes device-code login."""
    global _access_token, _auth_status

    try:
        token = _app.acquire_token_by_device_flow(_flow)
        if "access_token" in token:
            with _auth_lock:
                _access_token = token["access_token"]
                _auth_status = "success"
        else:
            with _auth_lock:
                _auth_status = "failed"
    except Exception:
        with _auth_lock:
            _auth_status = "failed"


def start_token_polling() -> None:
    """Launch background thread to wait for user authentication."""
    thread = threading.Thread(target=_poll_for_token, daemon=True)
    thread.start()


def get_auth_status() -> str:
    with _auth_lock:
        return _auth_status


def get_access_token() -> str | None:
    with _auth_lock:
        return _access_token


def get_headers() -> dict:
    token = get_access_token()
    if not token:
        raise RuntimeError("Not authenticated — no access token available.")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
