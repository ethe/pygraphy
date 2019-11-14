Pygraphy supports GraphQL introspection, and it has already integrated the [GraphQL Playground](https://github.com/prisma/graphql-playground). Try to run the web server which is posted in the quick review at [Introduction](/) and visit [http://0.0.0.0:8000](http://0.0.0.0:8000) by a browser, then you can enjoy the playground in developing.

![Playground](./static/playground.jpg)

The schema of Introspection are totally wrote with Pygraphy itself: [pygraphy/introspection.py](https://github.com/ethe/pygraphy/blob/master/pygraphy/introspection.py), which proves that Pygraphy has a powerful schema declaration availability.

## Playground Settings

Using the attribute of schema class `PLAYGROUND_SETTINGS` and customize playground settings.

```python
class Schema(pygraphy.Schema):

    PLAYGROUND_SETTINGS = {
        "request.credentials": "same-page"
    }

    query: Optional[Query]
```
