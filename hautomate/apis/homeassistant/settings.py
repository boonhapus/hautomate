from typing import Optional
import enum

from homeassistant.core import HomeAssistant
from pydantic import validator

from hautomate.settings import Settings


class Feed(enum.Enum):
    """
    Represent the current state of an Intent.
    """
    custom_component = 'CUSTOM_COMPONENT'
    websocket = 'WEBSOCKET'


class Config(Settings):
    """
    Validator to ensure proper HomeAssistant API configuration.

    Attributes
    ----------
    """
    feed: Feed
    hass_interface: Optional[HomeAssistant] = None

    @validator('feed', pre=True)
    def _str_upper(cls, enum_candidate):
        return enum_candidate.upper()

    @validator('hass_interface')
    def _check_feed(cls, hass, values):
        if values['feed'] == Feed.custom_component and hass is None:
            raise ValueError('regression error, the custom component seems to be broken!')

        return hass

    class Config:
        arbitrary_types_allowed = True
