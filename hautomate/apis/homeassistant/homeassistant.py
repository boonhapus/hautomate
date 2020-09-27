import asyncio
import logging

from homeassistant.core import HomeAssistant as HASS

from hautomate.apis.homeassistant.enums import HassFeed
from hautomate.context import Context
from hautomate.api import API, api_method, public_method


_log = logging.getLogger(__name__)


class HassInterface:

    def __init__(self, feed, hass):
        self.feed = feed
        self._hass = hass
        self._ws = None

        if not self.am_component:
            asyncio.create_task(self._connect_to_websocket())

    @property
    def am_component(self) -> bool:
        """
        Determine if the interface is a CUSTOM_COMPONENT.
        """
        return self.feed == HassFeed.custom_component

    async def _connect_to_websocket(self):
        """
        """
        pass

    #

    async def call_service(self, domain: str, service: str, service_data: dict):
        """
        TODO
        """
        if self.am_component:
            r = await self._hass.services.async_call(
                domain,
                service,
                service_data,
                # blocking=False,
                # limit=10,
            )
            return r
        # do websocket stuff

    async def fire_event(self, event_type: str, event_data: dict):
        """
        TODO
        """
        if self.am_component:
            self._hass.bus.async_fire(event_type, event_data)
            return
        # do websocket stuff


class HomeAssistant(API):
    """
    TODO
    """
    def __init__(self, hauto, *, feed: str, hass_interface: HASS=None):
        self.feed = feed
        self.hass_interface = HassInterface(feed, hass_interface)
        super().__init__(hauto)

    # Listeners and Internal Methods

    async def on_hass_event_receive(self, ctx: Context):
        """
        """
        pass

    # Public Methods

    @public_method
    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict=None,
        wait: bool=False
    ):
        """
        Call a service.

        Parameters
        ----------
        domain : str
          TODO

        service : str
          TODO

        service_data : dict = None
          TODO
        """
        if service_data is None:
            service_data = {}

        coro = self.hass_interface.call_service(domain, service, service_data)
        task = asyncio.create_task(coro)

        if wait:
            await task

    @public_method
    async def fire_event(self, event_type: str, event_data: dict=None):
        """
        Fire an event.

        Parameters
        ----------
        event_type : str
          TODO

        event_data: dict = None
          TODO
        """
        coro = self.hass_interface.fire(event_type, event_data)
        asyncio.create_task(coro)

    # Intents
