import json
import pytest
from starlette.testclient import TestClient
from examples.starwars.schema import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_get_playground(client):
    response = client.get('/')
    assert response.status_code == 200


def test_request(client):
    content = {
        'operationName': None,
        'query': "{\n  hero(episode: JEDI) {\n    id\n    name\n  }\n}\n",
        "variables": {}
    }
    response = client.post(
        '/', data=json.dumps(content), headers={'content-type': 'application/json'})
    assert response.status_code == 200
