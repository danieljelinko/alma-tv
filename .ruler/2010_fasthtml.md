# FastHTML + HTMX Rules

## Stack Snapshot
- FastHTML provides HTML-first routing on top of Starlette/Uvicorn; build views with Python FastTags (`Div`, `P`, `Card`, ...).

## References
- [fasthtml.mdc](mdc:.cursor/rules/fasthtml.mdc) – core FastHTML + HTMX patterns.

## Build Checklist
- [ ] Create apps with `app, rt = fast_app(hdrs=Theme.<palette>.headers())`; call `serve()` directly (no uvicorn wrapper).
- [ ] Define routes with `@rt` (GET/POST) or `@app.<method>`; return HTML tags or strings, not JSON APIs.
- [ ] Keep logic in small helpers; UI functions should compose tags and read like templates.

## HTMX Essentials
- FastHTML route functions stringify to their path, so `Button("Show", hx_get=my_route)` resolves to `/my_route`.
- Use `.to(...)` when you need to pass query/path params: `hx_get=my_route.to(item_id=5)` → `/my_route?item_id=5`.
- Prefer `hx_target` + `hx_swap` to update only the affected DOM node; wrap reusable pieces in helper functions that return tags.
- Forms default to POST; for GET updates use `hx_get`. Remember to set `hx_trigger` when the default (`change`) is not desired.

## Pattern Library
### File Upload Grid
```python
from base64 import b64encode
from fasthtml.common import *
from monsterui.all import *

app, rt = fast_app(hdrs=Theme.blue.headers())

@rt
def index():
    return DivCentered(
        Card(H3("Upload images"),
             Input(type="file", name="images", multiple=True,
                   hx_post=upload, hx_target="#image-list",
                   hx_swap="afterbegin", hx_trigger="change",
                   hx_encoding="multipart/form-data", accept="image/*")),
        Div(id="image-list"))

async def ImageCard(image):
    data = b64encode(await image.read()).decode()
    return Card(H4(image.filename), Img(src=f"data:{image.content_type};base64,{data}"))

@rt
async def upload(images: list[UploadFile]):
    return Grid(*[await ImageCard(img) for img in images])
```

### Cascading Dropdowns
```python
from fasthtml import ft
chapters = {...}; lessons = {...}

def select_box(label, name, options, **hx):
    return DivLAligned(FormLabel(label, for_=name),
                       ft.Select(ft.Option(f"-- select {label.lower()} --", disabled='', selected='', value=''),
                                 *map(ft.Option, options), name=name, **hx))

@rt
def get_lessons(chapter: str):
    return select_box("Lesson", "lesson", lessons[chapter])

@rt
def index():
    return Container(
        select_box("Chapter", "chapter", chapters,
                   hx_get=get_lessons, hx_target="#lessons"),
        Div(id="lessons"), cls='space-y-4')
```

### Infinite Scroll Table Rows
```python
column_names = ("name", "email", "id")

def table_chunk(page: int, size: int = 20):
    rows = [mk_row(i) for i in range((page-1)*size, page*size)]
    rows[-1].attrs.update({
        'hx_get': page_route.to(idx=page + 1),
        'hx_trigger': 'revealed',
        'hx_swap': 'afterend'})
    return rows

@rt
def index():
    return Titled('Infinite Scroll', Table(
        Thead(Tr(*[Th(col) for col in column_names])),
        Tbody(*table_chunk(1))))

@rt(name='page_route')
def page(idx: int = 1):
    return table_chunk(idx)
```

### Todo CRUD with Partial Swaps
- Model rows with Fastlite and patch `__ft__` to control rendering.
- Use `hx_target=f'#todo-{id}'` + `hx_swap='outerHTML'` so toggle/delete updates only one card.
- After upserts, return `(mk_todo_list(), mk_todo_form()(hx_swap_oob='true', hx_target='#todo-input'))` to refresh list and reset the form in one response.

## WebSockets + Sessions
Session data is shared between HTTP routes and websockets. Example:
```python
app = FastHTML(exts='ws')
rt = app.route

@rt('/login')
def login(session):
    session['person'] = 'Bob'
    return "ok"

@app.ws('/ws')
async def ws(msg: str, send, session):
    await send(Div(f"Hello {session.get('person')} {msg}", id='notifications'))
```

## Design Notes
- Keep scripts inline for tiny snippets; move larger JS into separate files but still mount via `Script(src=...)`.
- Prefer HTMX interactions over raw JS; fall back to vanilla JS only for capabilities HTMX cannot provide.
