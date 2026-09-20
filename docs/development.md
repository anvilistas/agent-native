# Limits and development


One `App` instance per consumer. Implements stateless JSON request/response MCP for protocol versions 2025-03-26, 2025-06-18 and 2025-11-25. Supports initialization, ping, tools and UI resources. GET streaming returns 405; notifications return 202 without invoking operations. No streaming, OAuth, task orchestration, subscriptions or server-initiated sampling.

Bounded reads and writes suit this adapter. Research, GitHub access and model generation stay in the agent. Anvil server events can independently update an already-open Form.

For custom authentication or endpoint registration, the lower-level `agent_native.mcp.Server` remains available.

## Development

```sh
pnpm --dir bridge install --ignore-workspace
pnpm --dir bridge build
python tests/test_mcp.py
python tests/test_connections.py
python tests/test_registration.py
anvil --json validate .
```

The generated `server_code/_assets.py` is committed and bundles the official MCP Apps SDK. Consumers need no Node build. Dev Updates is a consumer example; its business logic is outside this dependency.

## Documentation

The docs follow the MkDocs and Read the Docs theme approach used by Anvil Reactive. Build locally:

```sh
python -m pip install -r requirements-docs.txt
python -m mkdocs build --strict
```

The root `llms.txt` is the canonical compact guide for coding agents. A build hook copies it to the site root. Edit it when the public API or required setup changes. Do not include runtime debug URLs, bearer tokens or account-specific credentials in docs.

GitHub Pages publishes these docs at https://anvilistas.github.io/agent-native/. Pushes to `master` affecting documentation or its build files trigger deployment. The Read the Docs configuration remains available for an alternative host.
