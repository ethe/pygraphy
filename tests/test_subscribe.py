import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    from examples.starwars.schema import app
    return TestClient(app)


def test_request(client):
    with client.websocket_connect('/ws') as websocket:
        query = '''
        subscription test {
          beat {
            beat
            foo(arg: 2)
          }
        }
        '''
        data = {'query': query, 'variables': None}
        websocket.send_json(data)
        start = 0
        for i in range(10):
            data = websocket.receive_json()
            assert data == {'data': {'beat': start, 'foo': start * 2}, 'errors': None}
            start += 1
