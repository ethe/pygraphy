import pathlib
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse


def get_playground_html(request_path: str) -> str:
    here = pathlib.Path(__file__).parents[0]
    path = here / "static/playground.html"

    with open(path) as f:
        template = f.read()

    return template.replace("{{REQUEST_PATH}}", request_path)


class View(HTTPEndpoint):

    async def get(self, request):
        html = get_playground_html(str(request.url))
        return PlainTextResponse(html)

    async def post(self, request):
        pass
