from typing import Optional

from homeassistant.core import HomeAssistant
from pydantic import validator

from hautomate.apis.homeassistant.enums import HassFeed
from hautomate.settings import Settings


class Config(Settings):
    """
    Validator to ensure proper HomeAssistant API configuration.

    Attributes
    ----------
    feed : str, one of 'custom_component' or 'websocket', default 'websocket'
      where to source your HomeAssistant data from

    hass_interface : HomeAssistant, default None
      the homeassistant inferface
    """
    feed: HassFeed = 'WEBSOCKET'
    hass_interface: Optional[HomeAssistant] = None

    @validator('feed', pre=True)
    def _str_upper(cls, enum_candidate):
        return enum_candidate.upper()

    @validator('hass_interface')
    def _check_feed(cls, hass, values):
        if values['feed'] == HassFeed.custom_component and hass is None:
            raise ValueError('regression error, the custom component seems to be broken!')

        return hass

    class Config:
        arbitrary_types_allowed = True
