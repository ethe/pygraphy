import json
import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    from examples.starwars.schema import app
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

    content = "{\n  hero(episode: JEDI) {\n    id\n    name\n  }\n}\n"
    response = client.post(
        '/', data=content, headers={'content-type': 'application/graphql'})
    assert response.status_code == 200


def test_error(client):
    content = {
        'operationName': None,
        'query': "{\n  hero(episode: JEDI) {\n    id\n    name\n  }\n}\n",
        "variables": {}
    }
    response = client.post(
        '/', data=json.dumps(content), headers={'content-type': 'application/text'})
    assert response.status_code == 415
