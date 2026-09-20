from anvil import *
import anvil.js
import anvil.server
import anvil.users  # pyright: ignore[reportMissingImports]  # Users is supplied by the consuming app.
import json
from ._anvil_designer import ConnectionsTemplate


class Connections(ConnectionsTemplate):
    def __init__(self, routing_context=None, **properties):
        super().__init__(**properties)
        self.issued = None
        self.permissions_data = []
        self.connections.set_event_handler('x-revoke', self.revoke)
        if anvil.js.window.parent != anvil.js.window:
            self.sign_in.visible = False
            self.message.text = 'Open this page in its own tab to manage connections.'
            return
        self.load()

    def load(self):
        allowed = anvil.server.call('agent_native_connection_access')
        self.sign_in.visible = not allowed
        self.manager.visible = allowed
        if not allowed:
            return
        data = anvil.server.call('agent_native_connections_list')
        self.endpoint.text = data['url']
        self.connections.items = data['connections']
        if not self.permissions_data:
            self.permissions_data = [{'scope': scope, 'label': label, 'selected': False}
                                     for scope, label in data['permissions'].items()]
            self.permissions.items = self.permissions_data

    @handle('sign_in', 'click')
    def sign_in_click(self, **event_args):
        if anvil.users.login_with_form(show_signup_option=False, allow_cancel=True) is not None:
            self.load()
            if not self.manager.visible:
                self.message.text = 'This account cannot manage connections.'

    @handle('create', 'click')
    def create_click(self, **event_args):
        self.create.enabled = False
        try:
            result = anvil.server.call('agent_native_connections_create', self.connection_name.text,
                                      [p['scope'] for p in self.permissions_data if p['selected']])
            if not result['ok']:
                self.message.text = result['message']
                return
            self.issued = result
            self.token.text = result['token']
            self.new_connection.visible = True
            self.message.text = ''
            self.load()
        finally:
            self.create.enabled = self.issued is None

    @handle('copy_token', 'click')
    def copy_token_click(self, **event_args):
        if self.issued is None:
            return
        anvil.js.window.navigator.clipboard.writeText(self.issued['token'])
        self.message.text = 'Token copied.'

    @handle('copy_config', 'click')
    def copy_config_click(self, **event_args):
        if self.issued is None:
            return
        # JSON string quoting is compatible with TOML basic strings here.
        config = '[mcp_servers.anvil_app]\nurl = ' + json.dumps(self.issued['url'])
        config += '\n[mcp_servers.anvil_app.http_headers]\nAuthorization = ' + json.dumps('Bearer ' + self.issued['token']) + '\n'
        anvil.js.window.navigator.clipboard.writeText(config)
        self.message.text = 'Configuration copied.'

    @handle('done', 'click')
    def done_click(self, **event_args):
        self.issued = None
        self.token.text = ''
        self.new_connection.visible = False
        self.create.enabled = True

    def revoke(self, connection_id, **event_args):
        result = anvil.server.call('agent_native_connections_revoke', connection_id)
        if not result['ok']:
            self.message.text = result['message']
            return
        if self.issued and self.issued['id'] == connection_id:
            self.done_click()
        self.load()
