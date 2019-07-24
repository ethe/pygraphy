import os
import pytest
from starlette.testclient import TestClient


@pytest.fixture()
def client():
    from examples.starwars.schema import app
    return TestClient(app, raise_server_exceptions=False)


def test_subscription(client):
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
            assert data == {'data': {'beat': {'beat': start, 'foo': start * 2}}, 'errors': None}
            start += 1


def test_query(client):
    with client.websocket_connect('/ws') as websocket:
        query = """query IntrospectionQuery {
          __schema {
            queryType {
              name
            }
            mutationType {
              name
            }
            subscriptionType {
              name
            }
            types {
              ...FullType
            }
            directives {
              name
              description
              locations
              args {
                ...InputValue
              }
            }
          }
        }

        fragment FullType on __Type {
          kind
          name
          description
          fields(includeDeprecated: true) {
            name
            description
            args {
              ...InputValue
            }
            type {
              ...TypeRef
            }
            isDeprecated
            deprecationReason
          }
          inputFields {
            ...InputValue
          }
          interfaces {
            ...TypeRef
          }
          enumValues(includeDeprecated: true) {
            name
            description
            isDeprecated
            deprecationReason
          }
          possibleTypes {
            ...TypeRef
          }
        }

        fragment InputValue on __InputValue {
          name
          description
          type {
            ...TypeRef
          }
          defaultValue
        }

        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }"""
        data = {'query': query, 'variables': None}
        import json
        websocket.send_text(json.dumps(data))
        data = websocket.receive_text()
        path = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        with open(f'{path}/subscription_introspection', 'r') as f:
            assert data == f.read()[:-1]
