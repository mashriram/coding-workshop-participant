import json
import pytest
from test_utils import load_module

auth_module = load_module("auth-service", "function")

@pytest.fixture
def auth_mock_db(mocker):
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mocker.patch.object(auth_module, 'get_db_connection', return_value=mock_conn)
    mocker.patch.object(auth_module, 'release_connection')
    
    auth_module._db_initialized = True
    return mock_conn, mock_cursor

def test_login_success(auth_mock_db):
    conn, cur = auth_mock_db
    import bcrypt
    hashed = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
    cur.fetchone.return_value = (1, "Test User", "test@test.com", hashed, "employee", "IT")

    event = {
        "httpMethod": "POST",
        "path": "/auth-service/login",
        "body": json.dumps({"email": "test@test.com", "password": "testpass"})
    }

    resp = auth_module.handler(event, None)
    
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "token" in body
    assert body["user"]["email"] == "test@test.com"

def test_login_invalid_password(auth_mock_db):
    conn, cur = auth_mock_db
    import bcrypt
    hashed = bcrypt.hashpw(b"realpass", bcrypt.gensalt()).decode()
    cur.fetchone.return_value = (1, "Test User", "test@test.com", hashed, "employee", "IT")

    event = {
        "httpMethod": "POST",
        "path": "/auth-service/login",
        "body": json.dumps({"email": "test@test.com", "password": "wrongpass"})
    }

    resp = auth_module.handler(event, None)
    assert resp["statusCode"] == 401

def test_get_me_unauthorized():
    event = {
        "httpMethod": "GET",
        "path": "/auth-service/me",
        "headers": {}
    }
    
    resp = auth_module.handler(event, None)
    assert resp["statusCode"] == 401
    body = json.loads(resp["body"])
    assert body["error"] == "Authentication required"

def test_get_me_success(auth_mock_db):
    conn, cur = auth_mock_db
    token = auth_module.create_token(1, "test@test.com", "employee", "Test User")
    
    cur.fetchone.return_value = (1, "Test User", "test@test.com", "employee", "IT", "2024-01-01")

    event = {
        "httpMethod": "GET",
        "path": "/auth-service/me",
        "headers": {"Authorization": f"Bearer {token}"}
    }

    resp = auth_module.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["id"] == 1
