import logging

from homeassistant.core import HomeAssistant as HASS

from hautomate.api import API, api_method, public_method


_log = logging.getLogger(__name__)


class HomeAssistant(API):
    """
    TODO
    """
    def __init__(self, hauto, *, feed: str, hass_interface: HASS=None):
        self.feed = feed
        self.hass_interface = hass_interface or 'some_default_interface'
        super().__init__(hauto)
