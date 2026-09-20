"""Install one agent integration in a consuming Anvil app."""
from functools import wraps
import re

import anvil.server
import anvil.users  # pyright: ignore[reportMissingImports]  # Users is supplied by the consuming app.
from .mcp import Server, ToolResult
from ._assets import BRIDGE


class App(Server):
    def __init__(self, name, access, *, owner, permissions, instructions=''):
        super().__init__(name, access.authenticate, instructions=instructions)
        self.access = access
        self.permissions = permissions
        self.views = {}
        self.owner = owner
        anvil.server.http_endpoint('/mcp', methods=['POST', 'GET', 'DELETE'])(self.handle)
        anvil.server.http_endpoint('/agent-native/bridge.js', methods=['GET'])(self._bridge)
        register_callable('agent_native_client_url', self._client_url)
        register_callable('agent_native_claim', self._claim)
        register_callable('agent_native_connection_access', self._connection_access)
        for name, fn in [('list', self._connections), ('create', self._create), ('revoke', self._revoke)]:
            register_callable('agent_native_connections_' + name, fn, require_user=owner)

    def view(self, name, *, path, scope):
        if not re.fullmatch('[a-z][a-z0-9_]*', name) or name in self.views:
            raise ValueError('Use a unique view name containing lowercase letters, digits and underscores.')
        if not path.startswith('/') or path.startswith('//') or '#' in path or '?' in path:
            raise ValueError('Use a local application route for each view.')
        if scope not in self.permissions:
            raise ValueError('Declare the view permission in App permissions.')
        self.views[name] = {'path': path, 'scope': scope}
        def register(fn):
            @wraps(fn)
            def show(principal, **arguments):
                return ToolResult(fn(principal, **arguments), meta=self._launch(principal, name))
            self.tool(scope=scope, view=True, read_only=True)(show)
            def renew(principal):
                return ToolResult({'ok': True}, meta=self._launch(principal, name))
            renew.__name__ = 'reopen_' + name
            renew.__doc__ = 'Renew access to the ' + name + ' view.'
            self.tool(scope=scope, app_only=True, read_only=True)(renew)
            return show
        return register

    def _launch(self, principal, name):
        return {'anvil/runtimeUrl': anvil.server.get_app_origin().rstrip('/') + self.views[name]['path'],
                'anvil/embedTicket': self.access.ticket(principal, name),
                'anvil/renewTool': 'reopen_' + name}

    def _claim(self, view, ticket):
        config = self.views.get(view)
        if config is None:
            return {'ok': False, 'message': 'Unknown view.'}
        return self.access.claim(ticket, view, scope=config['scope'])

    def _bridge(self):
        return anvil.server.HttpResponse(200, BRIDGE, {'Content-Type': 'text/javascript', 'Cache-Control': 'no-store'})

    def _client_url(self):
        return anvil.server.get_api_origin().rstrip('/') + '/agent-native/bridge.js'

    def _connection_access(self):
        return bool(self.owner(anvil.users.get_user()))

    def _connections(self):
        subject = anvil.users.get_user()['email']
        return {'connections': self.access.connections(subject), 'permissions': self.permissions,
                'url': anvil.server.get_api_origin().rstrip('/') + '/mcp'}

    def _create(self, label, scopes):
        subject = anvil.users.get_user()['email']
        result = self.access.create_connection(subject, label, scopes, allowed=self.permissions)
        if result['ok']:
            result['url'] = anvil.server.get_api_origin().rstrip('/') + '/mcp'
        return result

    def _revoke(self, connection_id):
        subject = anvil.users.get_user()['email']
        return self.access.revoke_connection(subject, connection_id)


def register_callable(name, fn, *, require_user=None):
    # Anvil attaches registration metadata to functions; bound methods cannot
    # hold those attributes. Keep the actual callable as a normal function.
    @wraps(fn)
    def invoke(*args, **kwargs):
        return fn(*args, **kwargs)
    if require_user is None:
        anvil.server.callable(name)(invoke)
    else:
        anvil.server.callable(name=name, require_user=require_user)(invoke)
