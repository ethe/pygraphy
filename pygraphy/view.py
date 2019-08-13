import json
import pathlib
import dataclasses
from starlette import status
from starlette.websockets import WebSocket
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.responses import PlainTextResponse, HTMLResponse, Response
from .introspection import WithMetaSchema, WithMetaSubSchema
from .encoder import GraphQLEncoder
from .types.schema import Socket


def get_playground_html(request_path: str) -> str:
    here = pathlib.Path(__file__).parents[0]
    path = here / "static/playground.html"

    with open(path) as f:
        template = f.read()

    return template.replace("{{REQUEST_PATH}}", request_path)


class Schema(HTTPEndpoint, WithMetaSchema):

    async def get(self, request):
        html = get_playground_html(request.url.path)
        return HTMLResponse(html)

    async def post(self, request):
        content_type = request.headers.get("Content-Type", "")

        if "application/json" in content_type:
            data = await request.json()
        elif "application/graphql" in content_type:
            body = await request.body()
            text = body.decode()
            data = {"query": text}
        elif "query" in request.query_params:
            data = request.query_params
        else:
            return PlainTextResponse(
                "Unsupported Media Type",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        try:
            query = data["query"]
            variables = data.get("variables")
        except KeyError:
            return PlainTextResponse(
                "No GraphQL query found in the request",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        result = await self.execute(
            query, variables=variables, request=request
        )
        status_code = status.HTTP_200_OK if not result['errors'] else status.HTTP_400_BAD_REQUEST
        return Response(
            json.dumps(result, cls=GraphQLEncoder),
            status_code=status_code,
            media_type='application/json'
        )


@dataclasses.dataclass
class StarletteSocket(Socket):
    websocket: WebSocket

    async def send(self, text):
        return await self.websocket.send_text(text)

    async def receive(self):
        return await self.websocket.receive_text()

    async def close(self):
        # We have handled close event in schema executor, so reset it
        from starlette.websockets import WebSocketState
        self.websocket.client_state = WebSocketState.CONNECTED

        async def fake_receiver():
            return {"type": "websocket.disconnect"}
        self.websocket._receive = fake_receiver


class SubscribableSchema(WebSocketEndpoint, WithMetaSubSchema):

    async def on_connect(self, websocket):
        await websocket.accept()
        socket = StarletteSocket(websocket)
        try:
            await self.execute(
                socket
            )
        finally:
            await websocket.close()
