import enum


class HassFeed(enum.Enum):
    """
    Represent the way hautomate.HomeAssistant consumer type.
    """
    custom_component = 'CUSTOM_COMPONENT'
    websocket = 'WEBSOCKET'
