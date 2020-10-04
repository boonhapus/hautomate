from typing import Union, Callable
import asyncio
import logging

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant as HASS, State

from hautomate.apis.homeassistant.compat import HassWebConnector
from hautomate.apis.homeassistant.events import (
    HASS_STATE_CHANGED, HASS_ENTITY_CREATE, HASS_ENTITY_REMOVE, HASS_ENTITY_UPDATE,
    HASS_ENTITY_CHANGE
)
from hautomate.apis.homeassistant.enums import HassFeed
from hautomate.context import Context
from hautomate.intent import Intent
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
        Called when Home Assistant forwards an event to Hauto.
        """
        event = ctx.event_data['hass_event']

        if event.event_type == EVENT_STATE_CHANGED:
            await self.fire(HASS_STATE_CHANGED, **event.data)
            return

        # UNUSED EVENTS
        # - TIME_CHANGED
        # - SERVICE_REGISTERED
        # - CALL_SERVICE
        # - SERVICE_EXECUTED
        # - AUTOMATION_RELOADED
        # - SCENE_RELOADED
        # - PLATFORM_DISCOVERED
        # - COMPONENT_LOADED
        #
        # - HOMEASSISTANT_CLOSE
        # - HOMEASSISTANT_STOP
        #
        await self.fire(event.event_type, **event.data)

    async def on_hass_state_changed(self, ctx: Context):
        """
        Called when a Home Assistant Entity is updated.
        """
        entity_id = ctx.event_data['entity_id']
        old = ctx.event_data['old_state']
        new = ctx.event_data['new_state']

        if (
            old is not None
            and new is not None
            and old.state == new.state
            and old.attributes != new.attributes
        ):
            await self.fire(HASS_ENTITY_UPDATE, entity_id=entity_id, old_entity=old, new_entity=new)

        if old is None:
            await self.fire(HASS_ENTITY_CREATE, entity_id=entity_id)
            return

        if new is None:
            await self.fire(HASS_ENTITY_REMOVE, entity_id=entity_id)
            return

        if old.state != new.state:
            await self.fire(HASS_ENTITY_CHANGE, entity_id=entity_id, old_entity=old, new_entity=new)
            return

        _log.warning(
            f'somehow we made it past all the possible state updates:'
            f'\n    entity_id={entity_id}'
            f'\n    old_state={old}'
            f'\n    new_state={new}'
        )

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
        *,
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

    @api_method
    def monitor(
        self,
        entity_id: str,
        *,
        mode: str='CHANGE',
        fn: Callable,
        **intent_kwargs
    ) -> Intent:
        """
        Monitor an Entity for changes.



        # https://www.home-assistant.io/docs/automation/trigger
        #   /#numeric-state-trigger
        #   /#state-trigger
        """
        _ACCEPTED_MODES = {
            'CREATE': HASS_ENTITY_CREATE,     # when a new Entity is created
            'REMOVE': HASS_ENTITY_REMOVE,     # when an existing Entity is removed
            'CHANGE': HASS_ENTITY_CHANGE,     # when an Entity's state changes
            'ATTRIBUTE': HASS_ENTITY_UPDATE,  # when an Entity's attributes change
            'UPDATE': HASS_STATE_CHANGED      # literally any of the above
        }

        if mode.upper() not in _ACCEPTED_MODES:
            raise ValueError(f"keyword argument 'mode' must be one of: {_ACCEPTED_MODES}, got '{mode}'")

        event = _ACCEPTED_MODES[mode]

        # need check for: entity_id checking
        # need check for: from_state, to_state
        # need check for: above_value, below_value
        # - with logic for "inclusive" [off by default]
        # need logic for duration-check
        # - check which delegates, wait, delegates, returns?
        # - subclass of debounce?

        intent = Intent(event, fn=fn, **intent_kwargs)
        return intent
