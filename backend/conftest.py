import os
import sys
import pytest

# Add services to path so they can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "auth-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "employees-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "reviews-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "goals-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "training-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "development-service")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "competencies-service")))

# Mock environment variables
os.environ["JWT_SECRET"] = "test-secret"
os.environ["IS_LOCAL"] = "true"

@pytest.fixture
def mock_db(mocker):
    # Mock for a typical DB connection
    conn_mock = mocker.MagicMock()
    cursor_mock = mocker.MagicMock()
    
    # Enter context manager for standard 'with conn.cursor() as cur:'
    conn_mock.cursor.return_value.__enter__.return_value = cursor_mock
    
    return conn_mock, cursor_mock
