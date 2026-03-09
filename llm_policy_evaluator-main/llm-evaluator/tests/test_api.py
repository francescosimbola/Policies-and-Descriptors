from unittest.mock import Mock

from fastapi.testclient import TestClient

from src.api import get_llm_evaluator
from src.main import app
from src.models import PolicyResult, SysError

client = TestClient(app)

def test_api_body_missing_content() -> None:
    def mock_llm_evaluator() -> Mock:
        m = Mock()
        return m

    input_resource = {'policy': '', 'resourceId': '', 'resourceType': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_body_missing_policy() -> None:
    def mock_llm_evaluator() -> Mock:
        m = Mock()
        return m

    input_resource = {'content': '', 'resourceId': '', 'resourceType': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_body_missing_resource_id() -> None:
    def mock_llm_evaluator() -> Mock:
        m = Mock()
        return m

    input_resource = {'content': '', 'policy': '', 'resourceType': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_body_missing_resource_type() -> None:
    def mock_llm_evaluator() -> Mock:
        m = Mock()
        return m

    input_resource = {'content': '', 'policy': '', 'resourceId': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 400

    app.dependency_overrides = {}


def test_llm_evaluator_valid_response() -> None:
    def mock_llm_evaluator() -> Mock:
        m = Mock()
        m.evaluate.return_value = PolicyResult(satisfiesPolicy=True, errors=[], details={})
        return m

    input_resource = {'content': '', 'policy': '', 'resourceId': '', 'resourceType': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 200
    assert response.json() == {'satisfiesPolicy': True, 'errors': [], 'details': {}}

    app.dependency_overrides = {}


def test_llm_evaluator_invalid_response() -> None:
    def mock_llm_evaluator():
        m = Mock()
        m.evaluate.return_value = SysError(error='error')
        return m

    input_resource = {'content': '', 'policy': '', 'resourceId': '', 'resourceType': ''}

    app.dependency_overrides[get_llm_evaluator] = mock_llm_evaluator

    response = client.post('/v1/evaluate', json=input_resource)

    assert response.status_code == 500
    assert response.json() == {'error': 'error'}

    app.dependency_overrides = {}