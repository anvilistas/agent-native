from ._anvil_designer import EmbeddedLayoutTemplate


class EmbeddedLayout(EmbeddedLayoutTemplate):
    """Compact content layout for a Form shown inside a conversation."""
    def __init__(self, **properties):
        super().__init__(**properties)
