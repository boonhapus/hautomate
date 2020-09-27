from typing import Optional

from homeassistant.core import HomeAssistant
from pydantic import HttpUrl, validator

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
    host: Optional[HttpUrl] = None
    port: Optional[int] = 8123
    access_token: Optional[str] = None

    @validator('feed', pre=True)
    def _str_upper(cls, enum_candidate):
        return enum_candidate.upper()

    @validator('host', 'port', 'access_token', always=True)
    def _conditional_requires(cls, value, values):
        if values['feed'] == HassFeed.custom_component:
            return None

        if values['feed'] == HassFeed.websocket and value is None:
            raise ValueError('missing keyword argument')

        return value

    @validator('hass_interface')
    def _check_feed(cls, hass, values):
        if values['feed'] == HassFeed.custom_component and hass is None:
            raise ValueError('regression error, the custom component seems to be broken!')

        return hass

    class Config:
        arbitrary_types_allowed = True
