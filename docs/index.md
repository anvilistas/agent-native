# Agent-native Anvil apps

This prototype dependency exposes an Anvil app's server functions as MCP tools and its Forms as interactive views inside an agent conversation.

The agent runs in the host, such as Codex. Anvil stores the app's data and executes its operations. The dependency supplies the MCP endpoint, scoped connections and the bridge between an embedded Form and its conversation. No local MCP process, Uplink worker or model API key is needed for this path.

## Start here

- [Add agent access](quick-start.md): dependencies, tables, tools, routes and Forms.
- [Authentication](authentication.md): human login, connection tokens, view tickets and revocation.
- [API reference](api-reference.md): server decorators and client messaging.
- [Limits and development](development.md): supported transport, validation and wrapper builds.

The Dev Updates and Email Review apps exercise the same dependency with different data and Forms. Record authorization, revisions, unsent edits and approval rules remain app responsibilities.

## Status

The API is a prototype. Codex has been exercised with both consumer apps. Other MCP Apps hosts require compatibility checks, particularly authentication, nested iframes and conversation messaging. Ordinary MCP clients can use tools without rendering Forms.

Adding the dependency requires access to its Anvil app. Documentation is hosted on GitHub Pages. A public source repository does not itself grant access to the Anvil dependency app or establish a stable released dependency version. The current examples use development dependency versions; choose and test a released version before distributing a production consumer.
