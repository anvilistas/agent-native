# Authentication

The connection has three distinct credentials. The agent does not receive the user's password, and claiming a view does not log the browser into Anvil Users.

| Credential | Used by | Lifetime |
| --- | --- | --- |
| Anvil Users login | Human managing connections | Controlled by the consumer's Users service and remember-me settings |
| Connection bearer token | MCP host calling the app | No automatic expiry; valid until revoked or the subject is disabled |
| One-use launch ticket | Embedded Form opening a named view | 90 seconds to claim; creates a 15-minute server-session grant |

## First connection

1. The human opens `agent_native.Connections` in its own tab and signs in through the consumer's Users service.
2. The consumer's `owner(user)` predicate determines whether that account may manage connections. Despite the parameter name, apps can allow multiple accounts. Each manages only credentials whose subject matches their own email.
3. The human chooses a name and scopes. The dependency generates a bearer token, displays it once, and stores only its SHA-256 hash with its subject and permissions.
4. The human configures the MCP host with the app's endpoint and token. The supplied page can copy a Codex configuration snippet. Keep the resulting configuration private.

The token represents delegated access for that account. It is not a separate Users account. The current connection page does not create service accounts or let an owner issue tokens for another subject.

## Subsequent tool calls

The host sends `Authorization: Bearer <token>`. The dependency checks its hash, enabled state, the consumer's `enabled(subject)` callback and the tool's scope. Tools receive a trusted principal containing `subject`, `scopes` and `credential_id`.

The tool must still enforce record ownership and business rules. Having `records:write` does not authorize changing every record. Signing out of the human browser does not revoke an existing connection.

## Opening a Form

A tool decorated with `@app.view(...)` returns ordinary tool data plus UI metadata containing a launch ticket, route and renewal tool. The ticket stays out of model-visible tool content.

The host renders a wrapper that embeds the actual Anvil route. The Form calls `host.claim(view)`. The server consumes the ticket and records a grant for that named view in the Anvil server session. A valid existing grant can be reused on reload.

If claiming fails, the bridge asks the MCP host to invoke `reopen_<view>`. The host authenticates that request with its connection token and returns a fresh ticket. This is why the Form can reopen without another password prompt. Hosts must support server tool calls from the UI for renewal to work.

The grant is not an Anvil Users login. Embedded server callables should use `access.require_view(view)`, then enforce the relevant write scope and record rules. Do not assume `anvil.users.get_user()` identifies the embedded viewer.

## Revocation and approval

Revoking a connection disables subsequent MCP requests and embedded operations, including operations in an existing grant. Disabling the subject through the consumer's policy has the same effect. Already returned data cannot be withdrawn, and revocation does not cancel an operation already executing.

The connection grants only the scopes selected when it was created. Human approval remains separate app policy. A conversation message or an agent-authenticated call must not count as human approval unless the app deliberately defines it that way.

## Prototype boundaries

This is scoped bearer authentication, not OAuth. Tokens have no automatic expiration or rotation UI. Create a replacement and revoke the old connection to rotate one. Unclaimed expired ticket rows currently have no scheduled cleanup.

The connection-management page refuses to run in an iframe. Its protected server callables require the normal Users account predicate; a view ticket cannot create or revoke connections.
