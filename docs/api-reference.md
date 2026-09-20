# API reference

## Server

### `agent_native.app.App(name, access, *, owner, permissions, instructions='')`

Create one instance per consumer app. `access` is an `agent_native.access.Access` instance. `owner(user)` accepts or rejects the normal Users account managing connections. `permissions` maps scope strings to labels shown on the connection page.

Registers `/mcp`, `/agent-native/bridge.js` and the `agent_native_*` client callables. Reserve these names and paths for the dependency. User management and the connection Data Table belong to the consumer.

### `@app.tool(scope=..., read_only=False, schema=..., view=False, app_only=False)`

The first function argument is the authenticated principal; remaining arguments come from the tool input. Supply an object JSON Schema and reject additional properties. The default accepts no arguments. The function's name and docstring become the tool name and description.

Discovery and invocation both enforce `scope`. `read_only` is a host annotation, not a security control. Keep scopes in the `permissions` catalogue. Use the higher-level view decorator for ordinary embedded Forms.

### `@app.view(name, *, path, scope)`

Register a tool that opens a Form and returns its data. The decorated function takes the principal. This API currently accepts no tool input arguments. Names use lowercase letters, digits and underscores; paths are local absolute application routes without a query or fragment. The scope must appear in `permissions`.

Also creates the app-only `reopen_<name>` tool. The view route must exist in the consumer. View registration does not authorize arbitrary server callables used by the Form.

### `agent_native.access.Access(table, enabled)`

`table` has `key` string and `snapshot` simpleObject columns, with client access disabled. `enabled(subject)` checks whether the account may still use agent access.

`require_view(name)` returns the current grant's principal or raises `PermissionError`. Check its scopes before writes and use its subject to filter records. See [authentication](authentication.md) for credential and ticket lifetimes.

### Lower-level transport

`agent_native.mcp.Server` and `ToolResult` remain available for custom integration. Prefer `App` unless supplying different authentication or endpoint registration. These low-level interfaces are prototype implementation APIs, not a promise of backward compatibility.

## Client

Import `from agent_native import host`.

| API | Behaviour |
| --- | --- |
| `host.claim(view)` | Returns a mapping containing `ok`, or a failure message. Attempts host-mediated renewal if the initial claim fails. Check it before loading data. |
| `host.send_message(text)` | Requests a message in the owning conversation. Does not save app data or guarantee the agent completes a requested action. |
| `host.set_context(value)` | Sends JSON model context through the host bridge. |
| `host.on_refresh(callback)` | Registers a callback for subsequent tool-result refreshes. |
| `host.capabilities()` | Reports the bridge's available host capabilities. |
| `host.connect()` | Returns the underlying JavaScript bridge, including local UI buffer helpers. |

Save edits in the app before sending feedback. If messaging fails after saving, offer a retry without repeating the write. Preserve unsent edits when refreshing data and reject stale revisions on the server.

`agent_native.EmbeddedLayout` has a `content` slot and no app navigation chrome. `agent_native.Connections` is a routeable Form for human connection management. The Connections Form consumes routing context without forwarding it to the template constructor. Consumer route Forms should do the same.
