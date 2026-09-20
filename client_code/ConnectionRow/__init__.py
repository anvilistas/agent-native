from anvil import *
from ._anvil_designer import ConnectionRowTemplate


class ConnectionRow(ConnectionRowTemplate):
    def __init__(self, **properties):
        super().__init__(**properties)

    @handle('revoke', 'click')
    def revoke_click(self, **event_args):
        self.parent.raise_event('x-revoke', connection_id=self.item['id'])
