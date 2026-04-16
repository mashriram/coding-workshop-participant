"""
Auth Service: User authentication and authorization with JWT.
Handles login, registration, and user profile management.
"""

import json
import logging
import os
import re
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from postgres_service import get_db_connection, release_connection

logger = logging.getLogger()
logger.setLevel(logging.INFO)

JWT_SECRET = os.getenv("JWT_SECRET", "acme-super-secret-jwt-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8

PG_CONFIG = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"user={os.getenv('POSTGRES_USER', '')} "
    f"password={os.getenv('POSTGRES_PASS', '')} "
    f"dbname={os.getenv('POSTGRES_NAME', '')} "
    f"connect_timeout=15"
)

IS_LOCAL = os.getenv("IS_LOCAL", "true") == "true"
if not IS_LOCAL:
    PG_CONFIG += " sslmode=require"

VALID_ROLES = ["admin", "manager", "hr", "employee"]

# ─── DDL ────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_db_connection(PG_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'employee',
                department VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        # Seed default roles
        users_to_seed = [
            ("ACME Admin", "admin@acme.com", "Admin@1234", "admin"),
            ("ACME HR", "hr@acme.com", "HR@1234", "hr"),
            ("ACME Manager", "manager@acme.com", "Manager@1234", "manager"),
            ("ACME Employee", "employee@acme.com", "Employee@1234", "employee"),
        ]
        for name, email, pwd, role in users_to_seed:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if not cur.fetchone():
                    hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                    cur.execute("""
                        INSERT INTO users (name, email, password_hash, role)
                        VALUES (%s, %s, %s, %s)
                    """, (name, email, hashed, role))
                    logger.info(f"Seeded user: {email}")
        conn.commit()
    release_connection(conn)

# ─── JWT helpers ─────────────────────────────────────────────────────────────

def create_token(user_id, email, role, name):
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user(event):
    auth_header = (event.get("headers") or {}).get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:]
    return decode_token(token)

def require_roles(event, allowed_roles):
    user = get_current_user(event)
    if not user:
        return None, unauthorized("Authentication required")
    if user["role"] not in allowed_roles:
        return None, forbidden("Insufficient permissions")
    return user, None

# ─── Response helpers ─────────────────────────────────────────────────────────

def response(status, data):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(data, default=str),
    }

def bad_request(msg): return response(400, {"error": msg})
def unauthorized(msg): return response(401, {"error": msg})
def forbidden(msg): return response(403, {"error": msg})
def not_found(msg): return response(404, {"error": msg})
def server_error(msg): return response(500, {"error": msg})

# ─── Handlers ────────────────────────────────────────────────────────────────

def handle_login(body):
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    if not email or not password:
        return bad_request("Email and password are required")

    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, password_hash, role, department FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        if not user:
            return unauthorized("Invalid email or password")
        user_id, name, user_email, password_hash, role, department = user
        if not bcrypt.checkpw(password.encode(), password_hash.encode()):
            return unauthorized("Invalid email or password")
        token = create_token(user_id, user_email, role, name)
        return response(200, {
            "token": token,
            "user": {"id": user_id, "name": name, "email": user_email, "role": role, "department": department}
        })
    finally:
        release_connection(conn)

def handle_register(body):
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    role = (body.get("role") or "employee").strip()

    if not name or not email or not password:
        return bad_request("Name, email, and password are required")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return bad_request("Invalid email format")
    if len(password) < 8:
        return bad_request("Password must be at least 8 characters")
    if role not in VALID_ROLES:
        role = "employee"

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return bad_request("Email already registered")
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, email, hashed, role)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        token = create_token(user_id, email, role, name)
        return response(201, {
            "token": token,
            "user": {"id": user_id, "name": name, "email": email, "role": role}
        })
    finally:
        release_connection(conn)

def handle_get_me(event):
    user = get_current_user(event)
    if not user:
        return unauthorized("Authentication required")
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, role, department, created_at FROM users WHERE id = %s", (user["sub"],))
            row = cur.fetchone()
        if not row:
            return not_found("User not found")
        user_id, name, email, role, dept, created_at = row
        return response(200, {"id": user_id, "name": name, "email": email, "role": role, "department": dept, "created_at": created_at})
    finally:
        release_connection(conn)

def handle_update_me(event, body):
    user = get_current_user(event)
    if not user:
        return unauthorized("Authentication required")
    name = (body.get("name") or "").strip()
    department = (body.get("department") or "").strip()
    updates = []
    params = []
    if name:
        updates.append("name = %s")
        params.append(name)
    if department:
        updates.append("department = %s")
        params.append(department)
    if not updates:
        return bad_request("No fields to update")
    params.append(user["sub"])
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s RETURNING id, name, email, role, department", params)
            row = cur.fetchone()
            conn.commit()
        if not row:
            return not_found("User not found")
        return response(200, {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]})
    finally:
        release_connection(conn)

def handle_list_users(event):
    user, err = require_roles(event, ["admin"])
    if err:
        return err
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, role, department, created_at FROM users ORDER BY created_at DESC")
            rows = cur.fetchall()
        return response(200, [{"id": r[0], "name": r[1], "email": r[2], "role": r[3], "department": r[4], "created_at": r[5]} for r in rows])
    finally:
        release_connection(conn)

def handle_update_user(event, user_id, body):
    user, err = require_roles(event, ["admin"])
    if err:
        return err
    role = (body.get("role") or "").strip()
    if role and role not in VALID_ROLES:
        return bad_request(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    name = (body.get("name") or "").strip()
    department = (body.get("department") or "").strip()
    updates = []
    params = []
    if role:
        updates.append("role = %s"); params.append(role)
    if name:
        updates.append("name = %s"); params.append(name)
    if department:
        updates.append("department = %s"); params.append(department)
    if not updates:
        return bad_request("No fields to update")
    params.append(user_id)
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s RETURNING id, name, email, role, department", params)
            row = cur.fetchone()
            conn.commit()
        if not row:
            return not_found("User not found")
        return response(200, {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "department": row[4]})
    finally:
        release_connection(conn)

def handle_delete_user(event, user_id):
    user, err = require_roles(event, ["admin"])
    if err:
        return err
    if str(user["sub"]) == str(user_id):
        return bad_request("Cannot delete your own account")
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            row = cur.fetchone()
            conn.commit()
        if not row:
            return not_found("User not found")
        return response(204, {})
    finally:
        release_connection(conn)

# ─── Main handler ─────────────────────────────────────────────────────────────

_db_initialized = False

def handler(event=None, context=None):
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            logger.error("DB init failed: %s", e)
            return server_error(f"Database initialization failed: {str(e)}")

    event = event or {}
    method = (event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "GET")).upper()
    path = event.get("path") or event.get("rawPath") or "/"
    path = path.rstrip("/")

    # Handle OPTIONS preflight
    if method == "OPTIONS":
        return response(200, {})

    try:
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except Exception:
                return bad_request("Invalid JSON body")

        # Route: POST /auth-service/login
        if method == "POST" and path.endswith("/login"):
            return handle_login(body)

        # Route: POST /auth-service/register
        if method == "POST" and path.endswith("/register"):
            return handle_register(body)

        # Route: GET /auth-service/me
        if method == "GET" and path.endswith("/me"):
            return handle_get_me(event)

        # Route: PUT /auth-service/me
        if method == "PUT" and path.endswith("/me"):
            return handle_update_me(event, body)

        # Route: GET /auth-service/users
        if method == "GET" and path.endswith("/users"):
            return handle_list_users(event)

        # Route: PUT /auth-service/users/{id}
        if method == "PUT" and "/users/" in path:
            uid = path.split("/users/")[-1].split("/")[0]
            return handle_update_user(event, uid, body)

        # Route: DELETE /auth-service/users/{id}
        if method == "DELETE" and "/users/" in path:
            uid = path.split("/users/")[-1].split("/")[0]
            return handle_delete_user(event, uid)

        return not_found("Endpoint not found")

    except Exception as e:
        logger.error("Handler error: %s", e, exc_info=True)
        return server_error(str(e))

if __name__ == "__main__":
    print(handler({"httpMethod": "POST", "path": "/auth-service/login",
                   "body": json.dumps({"email": "admin@acme.com", "password": "Admin@1234"})}))
