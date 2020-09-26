"""
Hautomate. A task automation library focused on home automation.

Component to integrate with gPodder.
For more details about this component, please refer to
https://github.com/boonhapus/Hautomate/example/custom_components/README.md
"""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import MATCH_ALL, SERVICE_RELOAD
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

# from hautomate.apis.homeassistant.events import HASS_EVENT_RECEIVE
from hautomate.settings import HautoConfig
from hautomate import Hautomate

from .const import DOMAIN, CONF_APPS_DIR


_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_APPS_DIR): cv.isdir
    })
})


async def async_setup(hass, config):
    """ """

    hass_data = {
        'latitude': hass.cofig.latitude,
        'longitude': hass.config.longitude,
        'elevation': hass.config.elevation,
        'timezone': hass.config.time_zone
    }

    hauto_data = {
        # 'api_configs': {
        #     'moment': ...,
        #     'homeassistant': ...
        # }
    }

    cfg = HautoConfig(apps_dir=config[DOMAIN][CONF_APPS_DIR], **hass_data, **hauto_data)
    hauto = Hautomate(cfg)
    await hauto.start()

    async def _stop_start(event):
        """ Handle reload service calls. """
        _LOGGER.debug('stopping hautomate')
        await hauto.stop()
        _LOGGER.debug('successfully stopped, restarting hautomate')
        await hauto.start()
        _LOGGER.debug('hautomate is up and ready for use!')

    async def _fire_event(event):
        """ Fire an event on the Hautomate EventBus """
        await hauto.bus.fire('HASS_EVENT_RECEIVE', parent='hass', event=event)

    hass.bus.async_listen(MATCH_ALL, _fire_event)
    hass.services.async_register(DOMAIN, SERVICE_RELOAD, _stop_start)
    return True


# class AppIntent(SwitchEntity):

#     async def turn_on(self, **kw) -> None:
#         """
#         """
#         self.intent.unpause()

#     async def turn_off(self, **kw) -> None:
#         """
#         """
#         self.intent.pause()
