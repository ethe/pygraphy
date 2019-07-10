import pygraphy
from typing import List, Optional
from starlette.applications import Starlette
import uvicorn


app = Starlette(debug=True)


class Episode(pygraphy.Enum):
    NEWHOPE = 4
    EMPIRE = 5
    JEDI = 6


class Character(pygraphy.Interface):
    """
    Character interface contains human and droid
    """
    id: str
    name: str
    appears_in: List[Episode]

    @pygraphy.field
    def friends(self) -> Optional[List['Character']]:
        return None


class Human(pygraphy.Object, Character):
    """
    Human object
    """
    home_planet: str


class Droid(pygraphy.Object, Character):
    """
    Driod object
    """
    primary_function: str


class Query(pygraphy.Query):

    @pygraphy.field
    def hero(self, episode: Episode) -> Optional[Character]:
        return None

    @pygraphy.field
    def human(self, id: str = '1234') -> Optional[Human]:
        return Human(
            id=id, name='foo', appears_in=[Episode.NEWHOPE, Episode.EMPIRE], home_planet='Mars'
        )

    @pygraphy.field
    def droid(self, id: str) -> Optional[Droid]:
        return None


@app.route('/')
class Schema(pygraphy.Schema):
    query: Optional[Query]


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
