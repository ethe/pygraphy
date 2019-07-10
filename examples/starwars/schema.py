import pygraphql
from typing import List, Optional
from starlette.applications import Starlette
import uvicorn


app = Starlette(debug=True)


class Episode(pygraphql.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6


class Character(pygraphql.Interface):
    """
    Character interface contains human and droid
    """
    id: str
    name: str
    appears_in: List[Episode]

    @pygraphql.field
    def friends(self) -> Optional[List['Character']]:
        return None


class Human(pygraphql.Object, Character):
    """
    Human object
    """
    home_planet: str


class Droid(pygraphql.Object, Character):
    """
    Driod object
    """
    primary_function: str


class Query(pygraphql.Query):

    @pygraphql.field
    def hero(self, episode: Episode) -> Optional[Character]:
        return None

    @pygraphql.field
    def human(self, id: str = '1234') -> Optional[Human]:
        return Human(
            id=id, name='foo', appears_in=[Episode.NEWHOPE, Episode.EMPIRE], home_planet='Mars'
        )

    @pygraphql.field
    def droid(self, id: str) -> Optional[Droid]:
        return None


@app.route('/')
class Schema(pygraphql.Schema):
    query: Optional[Query]


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
