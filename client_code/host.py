"""Client API for a Form displayed inside an MCP conversation."""
import anvil.js
import anvil.server

_bridge = None


def connect():
    global _bridge
    if _bridge is None:
        _bridge = anvil.js.import_from(anvil.server.call('agent_native_client_url'))
    return _bridge


def send_message(text):
    return connect().sendMessage(text)


def set_context(value):
    return connect().context(value)


def on_refresh(callback):
    connect().onRefresh(anvil.js.report_exceptions(callback))


def capabilities():
    return connect().capabilities()


def claim(view):
    bridge = connect()
    result = anvil.server.call('agent_native_claim', view, bridge.takeTicket())
    if not result['ok']:
        try:
            ticket = bridge.renew()
        except anvil.js.ExternalError:
            return result
        result = anvil.server.call('agent_native_claim', view, ticket)
    return result
