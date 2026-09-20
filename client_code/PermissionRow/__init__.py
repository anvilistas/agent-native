from ._anvil_designer import PermissionRowTemplate


class PermissionRow(PermissionRowTemplate):
    def __init__(self, **properties):
        super().__init__(**properties)
