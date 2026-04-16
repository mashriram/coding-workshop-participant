"""
Analytics Service: Aggregates metrics to answer key business questions.
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

def handle_skill_gaps(user):
    conn = get_db_connection(PG_CONFIG)
    query = """
        SELECT e.id, e.name, e.department, c.name as competency, 
               ec.current_level, ec.target_level
        FROM employee_competencies ec
        JOIN competencies c ON c.id = ec.competency_id
        JOIN employees e ON e.id = ec.employee_id
        WHERE ec.current_level < ec.target_level
          AND e.status = 'active'
    """
    args = []
    if user["role"] == "manager":
        query += " AND e.manager_id = %s"
        args.append(user["sub"])
    query += " ORDER BY e.department, e.name"
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
        keys = ["employee_id", "employee_name", "department", "competency", "current_level", "target_level"]
        return response(200, [dict(zip(keys, r)) for r in rows])
    finally:
        release_connection(conn)

def handle_high_potentials(user):
    conn = get_db_connection(PG_CONFIG)
    # High potential: avg rating >= 4.0 OR goals avg progress > 80%
    query = """
        SELECT e.id, e.name, e.department, e.job_title,
               COALESCE(AVG(pr.rating), 0) as avg_rating,
               COALESCE(AVG(g.progress), 0) as avg_goal_progress
        FROM employees e
        LEFT JOIN performance_reviews pr ON pr.employee_id = e.id
        LEFT JOIN goals g ON g.employee_id = e.id
        WHERE e.status = 'active'
    """
    args = []
    if user["role"] == "manager":
        query += " AND e.manager_id = %s"
        args.append(user["sub"])
    
    query += """
        GROUP BY e.id, e.name, e.department, e.job_title
        HAVING COALESCE(AVG(pr.rating), 0) >= 4.0 OR COALESCE(AVG(g.progress), 0) >= 80
        ORDER BY avg_rating DESC
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
        keys = ["employee_id", "employee_name", "department", "job_title", "avg_rating", "avg_goal_progress"]
        # Convert Decimals to float for JSON
        res = []
        for r in rows:
            d = dict(zip(keys, r))
            d["avg_rating"] = float(d["avg_rating"])
            d["avg_goal_progress"] = float(d["avg_goal_progress"])
            res.append(d)
        return response(200, res)
    finally:
        release_connection(conn)

def handle_attrition_risks(user):
    conn = get_db_connection(PG_CONFIG)
    # Attrition risk: recent review rating < 3.0
    query = """
        SELECT DISTINCT e.id, e.name, e.department, pr.rating, pr.period, pr.year
        FROM employees e
        JOIN performance_reviews pr ON pr.employee_id = e.id
        WHERE pr.rating < 3.0 AND e.status = 'active'
    """
    args = []
    if user["role"] == "manager":
        query += " AND e.manager_id = %s"
        args.append(user["sub"])
    query += " ORDER BY pr.year DESC, pr.period DESC"
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
        keys = ["employee_id", "employee_name", "department", "rating", "period", "year"]
        res = []
        for r in rows:
            d = dict(zip(keys, r))
            d["rating"] = float(d["rating"]) if d["rating"] else None
            res.append(d)
        return response(200, res)
    finally:
        release_connection(conn)

def handle_skills_distribution(user):
    conn = get_db_connection(PG_CONFIG)
    query = """
        SELECT c.category, c.name, AVG(ec.current_level) as avg_level, COUNT(ec.id) as assessment_count
        FROM competencies c
        JOIN employee_competencies ec ON ec.competency_id = c.id
        JOIN employees e ON e.id = ec.employee_id
        WHERE e.status = 'active'
    """
    args = []
    if user["role"] == "manager":
        query += " AND e.manager_id = %s"
        args.append(user["sub"])
    query += " GROUP BY c.category, c.name ORDER BY c.category, c.name"
    
    try:
        with conn.cursor() as cur:
            cur.execute(query, args)
            rows = cur.fetchall()
        keys = ["category", "competency_name", "avg_level", "assessment_count"]
        res = []
        for r in rows:
            d = dict(zip(keys, r))
            d["avg_level"] = float(d["avg_level"]) if d["avg_level"] else 0.0
            res.append(d)
        return response(200, res)
    finally:
        release_connection(conn)

def handler(event=None, context=None):
    event = event or {}
    method = (event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "GET")).upper()
    path = event.get("path") or event.get("rawPath") or "/"
    path = path.rstrip("/")

    if method == "OPTIONS":
        return response(200, {})

    try:
        user = get_current_user(event)
        if not user:
            return unauthorized("Authentication required")

        if method == "GET" and path.endswith("/skill-gaps"):
            return handle_skill_gaps(user)
        if method == "GET" and path.endswith("/high-potentials"):
            return handle_high_potentials(user)
        if method == "GET" and path.endswith("/attrition-risks"):
            return handle_attrition_risks(user)
        if method == "GET" and path.endswith("/distribution/skills"):
            return handle_skills_distribution(user)

        return not_found("Endpoint not found")
    except Exception as e:
        logger.error("Handler error: %s", e, exc_info=True)
        return server_error(str(e))
