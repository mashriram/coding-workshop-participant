"""Shared JWT decode utility for Lambda services."""
import os
import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "acme-super-secret-jwt-key-2024")
JWT_ALGORITHM = "HS256"


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


def get_current_user(event):
    auth_header = (event.get("headers") or {}).get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return decode_token(auth_header[7:])


def require_roles(event, allowed_roles):
    user = get_current_user(event)
    if not user:
        return None, _error(401, "Authentication required")
    if user.get("role") not in allowed_roles:
        return None, _error(403, "Insufficient permissions")
    return user, None


def _error(status, msg):
    import json
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps({"error": msg}),
    }
