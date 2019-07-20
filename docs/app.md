Pygraphy integrates [Starlette](https://www.starlette.io) as a default web server. You can install web-integrated Pygraphy with `pip install pygraphy[web]`, or manually install the Starlette. Pygraphy checked the local environment every times you import it, if Pygraphy find that Starlette has already been installed, the Schema type would be replaced automatically to a Starlette View Schema type, it is a valid Starlette endpoint class and you can use it as normal.
```python
import pygraphy
from starlette.applications import Starlette
import uvicorn


app = Starlette(debug=True)


# ...


@app.route('/')
class Schema(pygraphy.Schema):
    query: Optional[Query]


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

If you not installed Starlette, using Schema type as a Starlette endpoint would raise an exception.
