fastapi-extras
---------------

A series of extras and utilities that make using
[fastapi](https://github.com/tiangolo/fastapi) a little bit easier

### Features

- Modular and Configurable Session Management
- Synchronous Request Getter Utilities using Depends
- Helpers for using [pyderive dataclasses](https://github.com/imgurbot12/pyderive)

### Examples

Session Middleware

```python3
from fastapi import FastAPI
from fastapi_extras.session import SessionMiddleware

# drop in replacement for starlette SessionMiddleware
app = FastAPI()
app.add_middleware(SessionMiddleware)

# customizable and configurable storage interface
from fastapi_extras.session.fs import FileStore

app = FastAPI()
app.add_middleware(SessionMiddleware, store=FileStore())
```

Synchronous Getters

```python3
from fastapi import FastAPI, Request
from fastapi_extras.getters import form

app = FastAPI()

@app.post('/async')
async def async_form(request: Request):
    """collect form object using async function call"""
    form = await request.form()
    return form

@app.post('/sync')
def sync_form(request: Request, form = form()):
    """collect async form resource without async using dependency"""
    return form
```

Pyderive Helpers

```python3
from fastapi import FastAPI, Request
from fastapi_extras.session import SessionMiddleware
from fastapi_extras.getters import as_session
from pyderive.extensions.validate import BaseModel, IPv4

class Session(BaseModel):
    ip: IPv4

app = FastAPI()
app.add_middleware(SessionMiddleware)

@app.get('/start')
def start(request: Request) -> str:
    host = request.client.host if request.client else '127.0.0.1'
    request.session['ip'] = host
    return 'Session Started'

@app.get('/check')
def check(session: Session = as_session(Session)):
    return f'Your IPAddress is {session.ip!r}'
```
