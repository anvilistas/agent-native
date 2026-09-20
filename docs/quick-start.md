# Add agent access to an app


Add dependency `3FTTGXCYZDGP2LT5` (package `agent_native`) and routing `3PIDO5P3H4VPEMPL`. Enable embedding and add the Users service. Install `jsonschema==4.25.1` in the app's Python environment.

Create a server-only Data Table named `connections` with a string `key` column and simpleObject `snapshot` column. Then create one `App` instance in a server module:

```python
import anvil.users
from anvil.tables import app_tables
from agent_native.access import Access
from agent_native.app import App


def owner(user):
    return bool(user and user['enabled'] and user['confirmed_email'])


def enabled(subject):
    return owner(app_tables.users.get(email=subject))


access = Access(app_tables.connections, enabled)
app = App('My app', access, owner=owner,
          permissions={'records:read': 'Read records'})


@app.tool(scope='records:read', read_only=True)
def read_records(principal):
    """Read the records this connected user can access."""
    return records_for(principal['subject'])


@app.view('records', path='/records', scope='records:read')
def show_records(principal):
    """Open the records review."""
    return records_for(principal['subject'])
```

`records_for` is consumer code. Filter records by the trusted principal; a scope alone does not authorize access to another user's data. Tighten `owner` to the app's actual account policy. Dev Updates permits only its named owner.

`App` registers `/mcp`, the browser bridge endpoint, connection-management callables, and ticket claiming. The view decorator supplies the iframe resource metadata and an app-only renewal tool. Consumers do not construct launch tickets or bootstrap endpoints.

Use `schema=` on `@app.tool` for JSON Schema inputs; the default accepts no arguments. Forbid additional properties. Discovery and invocation both enforce scopes. Declare each tool's scope in `permissions` so users can grant it when creating connections.

## Routes and Forms

In the consumer's `routes` client module:

```python
from routing.router import Route


class Connections(Route):
    path = '/connections'
    form = 'agent_native.Connections'


class Records(Route):
    path = '/records'
    form = 'RecordsReview'
```

Launch routing from the startup module with `from routing.router import launch; launch()`. Route Form constructors should accept `routing_context=None` without forwarding it to the template constructor.

The connection page requires normal Users login and the `owner` predicate. Users name a connection, select permissions, and receive its token once. It can copy a Codex configuration snippet. Store that configuration privately. Revocation disables subsequent MCP requests and embedded calls immediately. The page refuses to run inside an iframe.

Use `agent_native.EmbeddedLayout` for a compact content-only layout with a `content` slot. Ordinary Forms also work. In the review Form, call `agent_native.host.claim('records')` and check its `ok` result before loading data. Server callables serving the Form must call `access.require_view('records')` and enforce any write scope and record ownership themselves.

`agent_native.host` provides:

- `claim(view)`: claim the launch ticket, renewing through the host if necessary.
- `send_message(text)`: send feedback into the owning conversation.
- `set_context(value)`: provide JSON UI context when supported by the host.
- `on_refresh(callback)`: react to another tool result.
- `capabilities()`: check whether conversation messaging is available.
- `connect()`: access the JS bridge, including local UI buffers.

Persist shared drafts in Data Tables. Keep unsent browser edits separately, and handle revision conflicts in consumer code. Sending a message does not itself save edits or apply an action.

