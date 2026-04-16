"""
Employees Service: CRUD operations for employee records.
"""

import json
import logging
import os
from postgres_service import get_db_connection, release_connection
from jwt_utils import get_current_user, require_roles

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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


def init_db():
    conn = get_db_connection(PG_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                department VARCHAR(255),
                job_title VARCHAR(255),
                hire_date DATE,
                manager_id INTEGER,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                phone VARCHAR(50),
                location VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        # Seed sample employees if empty
        cur.execute("SELECT COUNT(*) FROM employees;")
        if cur.fetchone()[0] == 0:
            sample = [
                ("Alice Johnson", "alice.johnson@acme.com", "Engineering", "Senior Engineer", "2020-03-15", 3, "active", "+1-555-0101", "New York"),
                ("Bob Smith", "bob.smith@acme.com", "Engineering", "Staff Engineer", "2018-07-01", 3, "active", "+1-555-0102", "San Francisco"),
                ("Carol White", "carol.white@acme.com", "Product", "Product Manager", "2019-11-20", 3, "active", "+1-555-0103", "Austin"),
                ("David Brown", "david.brown@acme.com", "HR", "HR Manager", "2017-05-10", 3, "active", "+1-555-0104", "Chicago"),
                ("Eve Davis", "eve.davis@acme.com", "Engineering", "Junior Engineer", "2022-01-15", 3, "active", "+1-555-0105", "New York"),
                ("Frank Miller", "frank.miller@acme.com", "Sales", "Sales Director", "2016-09-01", 1, "active", "+1-555-0106", "Boston"),
                ("Grace Lee", "grace.lee@acme.com", "Marketing", "Marketing Manager", "2021-06-01", 1, "active", "+1-555-0107", "Seattle"),
                ("Henry Wilson", "henry.wilson@acme.com", "Finance", "Finance Analyst", "2020-08-15", 1, "active", "+1-555-0108", "New York"),
            ]
            for s in sample:
                cur.execute("""
                    INSERT INTO employees (name, email, department, job_title, hire_date, manager_id, status, phone, location)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, s)
        conn.commit()
    release_connection(conn)


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


def row_to_dict(row):
    keys = ["id", "name", "email", "department", "job_title", "hire_date",
            "manager_id", "status", "phone", "location", "created_at", "updated_at"]
    return dict(zip(keys, row))


def check_manager_access(conn, user_id, target_employee_id):
    with conn.cursor() as cur:
        cur.execute("SELECT manager_id FROM employees WHERE id = %s", (target_employee_id,))
        row = cur.fetchone()
        return bool(row and str(row[0]) == str(user_id))


def handle_list(event):
    user = get_current_user(event)
    if not user:
        return unauthorized("Authentication required")

    params = event.get("queryStringParameters") or {}
    department = params.get("department")
    status = params.get("status")
    search = params.get("search")

    query = "SELECT id, name, email, department, job_title, hire_date, manager_id, status, phone, location, created_at, updated_at FROM employees WHERE 1=1"
    args = []
    if department:
        query += " AND department = %s"; args.append(department)
    if status:
        query += " AND status = %s"; args.append(status)
    if search:
        query += " AND (name ILIKE %s OR email ILIKE %s OR job_title ILIKE %s)"; args += [f"%{search}%"] * 3
    if user["role"] == "manager":
        query += " AND manager_id = %s"; args.append(user["sub"])
    query += " ORDER BY name"

    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
        return response(200, [row_to_dict(r) for r in rows])
    finally:
        release_connection(conn)


def handle_get_one(event, emp_id):
    user = get_current_user(event)
    if not user:
        return unauthorized("Authentication required")
    conn = get_db_connection(PG_CONFIG)
    try:
        if user["role"] == "manager" and not check_manager_access(conn, user["sub"], emp_id):
            return forbidden("Not authorized to view this employee")
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, email, department, job_title, hire_date, manager_id, status, phone, location, created_at, updated_at FROM employees WHERE id = %s", (emp_id,))
            row = cur.fetchone()
        if not row:
            return not_found("Employee not found")
        return response(200, row_to_dict(row))
    finally:
        release_connection(conn)


def handle_create(event, body):
    user, err = require_roles(event, ["admin", "manager", "hr"])
    if err:
        return err
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    if not name or not email:
        return bad_request("Name and email are required")

    if user["role"] == "manager":
        body["manager_id"] = user["sub"]

    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM employees WHERE email = %s", (email,))
            if cur.fetchone():
                return bad_request("Email already exists")
            cur.execute("""
                INSERT INTO employees (name, email, department, job_title, hire_date, manager_id, status, phone, location)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, email, department, job_title, hire_date, manager_id, status, phone, location, created_at, updated_at
            """, (name, email, body.get("department"), body.get("job_title"),
                  body.get("hire_date") or None, body.get("manager_id") or None,
                  body.get("status", "active"), body.get("phone"), body.get("location")))
            row = cur.fetchone()
            conn.commit()
        return response(201, row_to_dict(row))
    finally:
        release_connection(conn)


def handle_update(event, emp_id, body):
    user, err = require_roles(event, ["admin", "manager", "hr"])
    if err:
        return err

    conn = get_db_connection(PG_CONFIG)
    if user["role"] == "manager":
        if not check_manager_access(conn, user["sub"], emp_id):
            release_connection(conn)
            return forbidden("Not authorized to update this employee")
        if "manager_id" in body and str(body["manager_id"]) != str(user["sub"]):
            release_connection(conn)
            return forbidden("Managers cannot reassign employees to other managers")

    fields = ["name", "email", "department", "job_title", "hire_date", "manager_id", "status", "phone", "location"]
    updates = []
    params = []
    for f in fields:
        if f in body:
            updates.append(f"{f} = %s")
            params.append(body[f] if body[f] != "" else None)
    if not updates:
        release_connection(conn)
        return bad_request("No fields to update")
    params.append(emp_id)

    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE employees SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s RETURNING id, name, email, department, job_title, hire_date, manager_id, status, phone, location, created_at, updated_at", params)
            row = cur.fetchone()
            conn.commit()
        if not row:
            return not_found("Employee not found")
        return response(200, row_to_dict(row))
    finally:
        release_connection(conn)


def handle_delete(event, emp_id):
    user, err = require_roles(event, ["admin"])
    if err:
        return err
    conn = get_db_connection(PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE employees SET status = 'inactive', updated_at = NOW() WHERE id = %s RETURNING id", (emp_id,))
            row = cur.fetchone()
            conn.commit()
        if not row:
            return not_found("Employee not found")
        return response(204, {})
    finally:
        release_connection(conn)


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

    if method == "OPTIONS":
        return response(200, {})

    try:
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"])
            except Exception:
                return bad_request("Invalid JSON body")

        # Extract ID from path
        parts = [p for p in path.split("/") if p]
        emp_id = None
        if len(parts) >= 2 and parts[-1].isdigit():
            emp_id = int(parts[-1])

        if method == "GET" and emp_id is None:
            return handle_list(event)
        if method == "GET" and emp_id:
            return handle_get_one(event, emp_id)
        if method == "POST":
            return handle_create(event, body)
        if method == "PUT" and emp_id:
            return handle_update(event, emp_id, body)
        if method == "DELETE" and emp_id:
            return handle_delete(event, emp_id)

        return not_found("Endpoint not found")
    except Exception as e:
        logger.error("Handler error: %s", e, exc_info=True)
        return server_error(str(e))


if __name__ == "__main__":
    print(handler({"httpMethod": "GET", "path": "/employees-service"}))
