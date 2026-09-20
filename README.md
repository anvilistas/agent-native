# Agent-native Anvil dependency

Expose an Anvil app's Python operations and Forms to an existing agent conversation. The consuming app hosts its own MCP HTTP endpoint. No model runs in this dependency.

Documentation: [quick start](docs/quick-start.md), [authentication](docs/authentication.md), [API reference](docs/api-reference.md). Coding agents can start with the root [llms.txt](llms.txt). Build the MkDocs site with `python -m mkdocs build --strict`; GitHub Pages deploys the docs from `master` to https://anvilistas.github.io/agent-native/.

## Consumer setup

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

## Authentication and isolation

Connections store only the token's SHA-256 hash, subject, scopes and enabled state. `enabled(subject)` is checked on every authenticated request and embedded operation. Connection listing and revocation are restricted to the signed-in account's own credentials.

This prototype uses scoped bearer credentials. It does not implement OAuth discovery or consent. Never put Server Uplink keys or owner passwords in MCP configuration or browser code.

A one-use launch ticket lasts 90 seconds and grants a 15-minute Anvil session for one view. Existing sessions survive reload; the wrapper can request another ticket through the authenticated MCP host when needed. Tickets remain in UI metadata, outside model-visible tool data. Agent access does not grant human approval permissions.

The wrapper checks the iframe origin and window before relaying messages. The app pins its parent origin during the channel handshake. CSP permits the consuming app's frame origin.

## Transport and limits

One `App` instance per consumer. Implements stateless JSON request/response MCP for protocol versions 2025-03-26, 2025-06-18 and 2025-11-25. Supports initialization, ping, tools and UI resources. GET streaming returns 405; notifications return 202 without invoking operations. No streaming, OAuth, task orchestration, subscriptions or server-initiated sampling.

Bounded reads and writes suit this adapter. Research, GitHub access and model generation stay in the agent. Anvil server events can independently update an already-open Form.

For custom authentication or endpoint registration, the lower-level `agent_native.mcp.Server` remains available.

## Development

```sh
pnpm --dir bridge install --ignore-workspace
pnpm --dir bridge build
python tests/test_mcp.py
python tests/test_connections.py
anvil --json validate .
```

The generated `server_code/_assets.py` is committed and bundles the official MCP Apps SDK. Consumers need no Node build. Dev Updates is a consumer example; its business logic is outside this dependency.
