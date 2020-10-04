from typing import Union
import asyncio
import logging

from homeassistant.core import HomeAssistant as HASS
from homeassistant.core import HomeAssistant as HASS, State

from hautomate.apis.homeassistant.compat import HassWebConnector
from hautomate.apis.homeassistant.enums import HassFeed
from hautomate.context import Context
from hautomate.api import API, api_method, public_method


_log = logging.getLogger(__name__)


class HassInterface:

    def __init__(
        self,
        feed: HassFeed,
        hass: Union[HASS, HassWebConnector],
    ):
        self.feed = feed
        self._hass = hass

        if not self.am_component:
            asyncio.create_task(self._hass.ws_auth_flow())

    @property
    def am_component(self) -> bool:
        """
        Determine if the interface is a CUSTOM_COMPONENT.
        """
        return self.feed == HassFeed.custom_component

    #

    def get_entity(self, entity_id: str) -> State:
        """
        TODO
        """
        if self.am_component:
            return self._hass.states.get(entity_id)

        raise NotImplementedError(
            'recording a copy of all states has not yet been registered for '
            'the websocket implementation'
        )

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict
    ) -> Union[bool, None]:
        """
        TODO
        """
        if self.am_component:
            fn = self._hass.services.async_call
        else:
            fn = self._hass.call_service

        return await fn(domain, service, service_data)#, blocking=False, limit=10)

    async def fire_event(self, event_type: str, event_data: dict) -> None:
        """
        TODO
        """
        if self.am_component:
            self._hass.bus.async_fire(event_type, event_data)
        else:
            await self._hass.fire_event(event_type, event_data)


class HomeAssistant(API):
    """
    TODO
    """
    def __init__(
        self,
        hauto,
        *,
        feed: str,
        hass_interface: HASS=None,
        **hass_interface_kw
    ):
        if hass_interface is None:
            hass_interface = HassWebConnector(loop=hauto.loop, **hass_interface_kw)

        self.feed = feed
        self.hass_interface = HassInterface(feed, hass_interface)
        super().__init__(hauto)

    # Listeners and Internal Methods

    async def on_hass_event_receive(self, ctx: Context):
        """
        """
        pass

    # Public Methods

    @public_method  # safe_sync? depends on ws-interface impl.
    def get_entity(self, entity_id: str) -> State:
        """
        Retrieve state of entity_id or None if not found.
        """
        return self.hass_interface.get_entity(entity_id)

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
        coro = self.hass_interface.call_service(domain, service, service_data)
        task = asyncio.create_task(coro)

        if wait:
            await task

    @public_method
    async def turn_on(self, entity_id: str, *, wait: bool=False, **data):
        """
        Generic service to turn devices on under any domain.

        Parameters
        ----------
        entity_id : str
          TODO

        wait : bool = False
          TODO

        **data
          service data to be sent into the service call
        """
        data['entity_id'] = entity_id
        await self.call_service('homeassistant', 'turn_on', service_data=data, wait=wait)

    @public_method
    async def turn_off(self, entity_id: str, wait: bool=False):
        """
        Generic service to turn devices off under any domain.

        Parameters
        ----------
        entity_id : str
          TODO

        wait : bool = False
          TODO
        """
        data = {'entity_id': entity_id}
        await self.call_service('homeassistant', 'turn_off', service_data=data, wait=wait)

    @public_method
    async def toggle(self, entity_id: str, *, wait: bool=False, **data):
        """
        Generic service to toggle devices on/off under any domain.

        Parameters
        ----------
        entity_id : str
          TODO

        wait : bool = False
          TODO

        **data
          service data to be sent into the service call
        """
        data['entity_id'] = entity_id
        await self.call_service('homeassistant', 'turn_off', service_data=data, wait=wait)

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
        await self.hass_interface.fire_event(event_type, event_data)

    # Intents
