import json
import pytest
from test_utils import load_module

emp_module = load_module("employees-service", "function")
auth_jwt = load_module("auth-service", "function")

@pytest.fixture
def employees_mock_db(mocker):
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mocker.patch.object(emp_module, 'get_db_connection', return_value=mock_conn)
    mocker.patch.object(emp_module, 'release_connection')
    
    emp_module._db_initialized = True
    return mock_conn, mock_cursor

def test_list_employees(employees_mock_db):
    conn, cur = employees_mock_db
    token = auth_jwt.create_token(1, "hr@acme.com", "hr", "HR User")
    
    cur.fetchall.return_value = [
        (1, "Alice", "alice@acme.com", "Engineering", "Dev", "2024-01-01", None, "active", "123", "NY", "2024-01-01", "2024-01-01"),
        (2, "Bob", "bob@acme.com", "Sales", "Rep", "2024-01-01", 1, "active", "123", "LA", "2024-01-01", "2024-01-01")
    ]

    event = {
        "httpMethod": "GET",
        "path": "/employees-service",
        "headers": {"Authorization": f"Bearer {token}"}
    }

    resp = emp_module.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body) == 2
    assert body[0]["name"] == "Alice"

def test_create_employee_unauthorized(employees_mock_db):
    token = auth_jwt.create_token(1, "emp@acme.com", "employee", "Emp User")
    
    event = {
        "httpMethod": "POST",
        "path": "/employees-service",
        "headers": {"Authorization": f"Bearer {token}"},
        "body": json.dumps({"name": "New Guy", "email": "new@guy.com"})
    }

    resp = emp_module.handler(event, None)
    assert resp["statusCode"] == 403
