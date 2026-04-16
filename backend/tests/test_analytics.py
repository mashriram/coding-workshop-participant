import json
import pytest
from test_utils import load_module

an_module = load_module("analytics-service", "function")
auth_jwt = load_module("auth-service", "function")

@pytest.fixture
def analytics_mock_db(mocker):
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mocker.patch.object(an_module, 'get_db_connection', return_value=mock_conn)
    mocker.patch.object(an_module, 'release_connection')
    
    return mock_conn, mock_cursor

def test_attrition_risks(analytics_mock_db):
    conn, cur = analytics_mock_db
    token = auth_jwt.create_token(1, "hr@acme.com", "hr", "HR User")
    
    cur.fetchall.return_value = [
        (1, "Alice", "Engineering", 2.5, "Q4", 2024),
    ]

    event = {
        "httpMethod": "GET",
        "path": "/analytics-service/attrition-risks",
        "headers": {"Authorization": f"Bearer {token}"}
    }

    resp = an_module.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body) == 1
    assert body[0]["rating"] == 2.5

def test_high_potentials(analytics_mock_db):
    conn, cur = analytics_mock_db
    token = auth_jwt.create_token(1, "admin@acme.com", "admin", "Admin User")
    
    cur.fetchall.return_value = [
        (2, "Bob", "Sales", "Rep", 4.5, 90),
    ]

    event = {
        "httpMethod": "GET",
        "path": "/analytics-service/high-potentials",
        "headers": {"Authorization": f"Bearer {token}"}
    }

    resp = an_module.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body) == 1
    assert body[0]["avg_rating"] == 4.5
    assert body[0]["avg_goal_progress"] == 90
