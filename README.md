# Agent-native Anvil dependency

Prototype for exposing an Anvil app's Python operations and Forms to an existing agent conversation. The consuming app hosts its own MCP HTTP endpoint. No model runs in this dependency.

## Consumer setup

Add dependency app `3FTTGXCYZDGP2LT5`. Its package is `agent_native`. The supplied review example also uses routing `3PIDO5P3H4VPEMPL`; routing is optional for the transport itself.

Create a server module with explicit tools and an endpoint:

```python
import anvil.server
from agent_native.mcp import Server

# authenticate(header) must return None or a trusted principal containing scopes.
server = Server('My app', authenticate)

@server.tool(scope='records:read', read_only=True)
def read_records(principal):
    """Read the records this connected user can access."""
    return {'records': records_for(principal['subject'])}

@anvil.server.http_endpoint('/mcp', methods=['POST', 'GET', 'DELETE'])
def endpoint():
    return server.handle()
```

`authenticate` and `records_for` above are consumer-defined functions. Every tool receives the authenticated principal as its first argument. Use `schema=` to supply its JSON Schema inputs; the default accepts no arguments. Additional properties should be forbidden. Tool discovery and every invocation check the declared scope. Record-level authorization remains in the app function.

Tools marked `view=True` advertise the standard iframe resource. Return `ToolResult(data, meta=...)` with `anvil/runtimeUrl`, `anvil/embedTicket`, and optionally `anvil/renewTool`. The launch URL must be a trusted app route. UI credentials belong in metadata, never in the model-visible data.

The current adapter needs `jsonschema==4.25.1` available in the consuming app's Python environment. A matching requirements file is included here.

## Embedded Forms

Use `agent_native.EmbeddedLayout` for a compact content-only layout. Its slot is `content`. Ordinary Forms also work.

`agent_native.host` exposes:

- `claim(claim_function)`: claim the launch ticket; attempt host-mediated renewal when the session is missing or expired.
- `send_message(text)`: submit feedback into the owning conversation.
- `set_context(value)`: provide JSON UI context when the host supports it.
- `on_refresh(callback)`: reload saved state when another tool result arrives.
- `capabilities()`: check whether conversation messaging is available.
- `connect()`: access the underlying JS bridge for local UI buffers and advanced integration.

The consumer currently supplies two small bootstrap functions, demonstrated in Dev Updates' `NativeReview` server module: `agent_native_client_url` returns the bridge's absolute API URL, and an HTTP endpoint serves `agent_native._assets.BRIDGE` with `Content-Type: text/javascript`. This avoids relying on dependency theme-asset URL conventions. The consumer also supplies a callable that invokes `Access.claim(ticket, view)`.

The wrapper embeds the actual app route. It validates the iframe's browser origin and window before relaying messages. The app pins its parent origin after the initial channel handshake. CSP allows only the consuming app's frame origin.

## Prototype authentication

`agent_native.access.Access(table, enabled)` uses a consumer-owned Data Table with a string `key` column and simpleObject `snapshot` column, with client access disabled. It does not share records between consuming apps.

Provision credentials in trusted server/admin code only. Generate 32 random bytes as a URL-safe token, store only its SHA-256 digest in `key` as `agent-native/credential/<digest>`, and store `{subject, scopes, enabled}` in `snapshot`. Give the raw token only to the connecting user's credential store. Disable or remove the record to revoke access. The `enabled(subject)` callback checks the app's user policy on every request and embedded read.

This is scoped bearer authentication for the prototype, not a complete OAuth login product. Never put Server Uplink keys or owner passwords in MCP configuration or browser code.

`Access.ticket(principal, view)` creates a one-use ticket valid for 90 seconds. Claiming it grants a 15-minute Anvil session for that view. Existing valid sessions survive reload; otherwise the wrapper can call an app-visible renewal tool through the authenticated MCP host. A failed renewal asks the user to reopen the view. Agent access does not grant human approval permissions.

## Transport and limits

Implements stateless JSON request/response MCP for protocol versions 2025-03-26, 2025-06-18 and 2025-11-25. Supports initialization, ping, tool listing/calls and static UI resource listing/reading. GET streaming returns 405; accepted notifications return 202 and never invoke tools. No streaming, OAuth discovery, task orchestration, subscriptions or server-initiated sampling.

Bounded reads and writes suit this adapter. Research, GitHub access and model generation stay in the agent. Use normal Anvil server events for an already-open Form's invalidation independently of MCP streaming.

Rebuilding the wrapper:

```sh
pnpm --dir bridge install --ignore-workspace
pnpm --dir bridge build
```

The generated `server_code/_assets.py` is committed so consumers need no Node build. It bundles the official MCP Apps SDK.

Run `python tests/test_mcp.py` in an environment containing jsonschema, then `anvil --json validate .`. Dev Updates is the integration example, not part of the dependency's business logic.
