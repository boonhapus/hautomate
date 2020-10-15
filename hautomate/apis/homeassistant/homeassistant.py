from typing import Union, Callable
import asyncio
import logging

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant as HASS, State, hass_Context

from hautomate.util.async_ import safe_sync
from hautomate.apis.homeassistant._compat import HassWebConnector
from hautomate.apis.homeassistant.checks import (
    EntityCheck, DiscreteValueCheck, ContinuousValueCheck
)
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

    def __init__(self, feed: HassFeed, hass: Union[HASS, HassWebConnector]):
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

    async def create_helper(
        self,
        entity_id: str,
        *,
        state: str,
        attributes: dict=None,
        ephemeral: bool=True
    ):
        """
        """
        if self.am_component:
            self._hass.states.async_set(
                entity_id, state, attributes, False, hass_Context()
            )
            return self._hass.states.get(entity_id)

        raise NotImplementedError(
            'creating a helper has not yet been registered for the websocket '
            'implementation'
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

        return await fn(domain, service, service_data)  # , blocking=False, limit=10)

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

    async def on_hass_state_change(self, ctx: Context):
        """
        Called when a Home Assistant Entity is updated.
        """
        entity_id = ctx.event_data['entity_id']
        old = ctx.event_data['old_state']
        new = ctx.event_data['new_state']

        if old is None:
            await self.fire(HASS_ENTITY_CREATE, entity_id=entity_id, new_entity=new)
            return

        if new is None:
            await self.fire(HASS_ENTITY_REMOVE, entity_id=entity_id, old_entity=old)
            return

        if old.state != new.state:
            await self.fire(HASS_ENTITY_CHANGE, entity_id=entity_id, old_entity=old, new_entity=new)
            return

        if old.attributes != new.attributes:
            await self.fire(HASS_ENTITY_UPDATE, entity_id=entity_id, old_entity=old, new_entity=new)
            return

        _log.warning(
            f'somehow we made it past all the possible state updates:'
            f'\n\tentity_id={entity_id}'
            f'\n\tstate equality: {old.state == new.state}'
            f'\n\tattrs equality: {old.attributes == new.attributes}'
            f'\n\told_state={old}'
            f'\n\tnew_state={new}'
        )

    # Public Methods

    @public_method
    @safe_sync
    def get_entity(self, entity_id: str) -> State:
        """
        Retrieve state of entity_id or None if not found.
        """
        return self.hass_interface.get_entity(entity_id)

    @public_method
    async def create_helper(self, entity_id: str):
        """
        TODO
        """
        return self.hass_interface.create_entity(entity_id)

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
        entity_id: str=None,
        *,
        domain: str=None,
        attribute: str=None,
        mode: str='CHANGE',
        duration: Union[int, str]=None,
        from_value: str=None,
        to_value: str=None,
        above_value: str=None,
        below_value: str=None,
        inclusive: bool=False,
        fn: Callable,
        **intent_kwargs
    ) -> Intent:
        """
        Monitor an Entity for changes.



        # https://www.home-assistant.io/docs/automation/trigger
        #   /#numeric-state-trigger
        #   /#state-trigger
        """
        # TODO
        if duration is not None:
            raise NotImplementedError('ComingSoon™')

        if not any((entity_id, domain)):
            raise TypeError(
                "HomeAssistant.monitor() missing 1 required positional or keyword "
                "argument: 'entity_id' or 'domain'"
            )

        if all((entity_id, domain)):
            raise TypeError(
                f"HomeAssistant.monitor() accepts either 'entity_id' or 'domain', but "
                f"not both, got: entity_id={entity_id}, domain={domain}"
            )

        if any((from_value, to_value)) and any((above_value, below_value, inclusive)):
            params = {
                'from_value': from_value, 'to_value': to_value,
                'above_value': above_value, 'below_value': below_value,
                'inclusive': inclusive
            }
            used = ', '.join([f"'{k}'" for k, v in params.items() if v is not None])
            raise TypeError(
                f"may not specify values for all the following arguments: {used}; "
                f"please mix 'from_value' and 'to_value' OR 'above_value', "
                f"'below_value', and 'inclusive'"
            )

        _ACCEPTED_MODES = {
            'CREATE': HASS_ENTITY_CREATE,     # when a new Entity is created
            'REMOVE': HASS_ENTITY_REMOVE,     # when an existing Entity is removed
            'CHANGE': HASS_ENTITY_CHANGE,     # when an Entity's state changes
            'ATTRIBUTE': HASS_ENTITY_UPDATE,  # when an Entity's attributes change
            'UPDATE': HASS_STATE_CHANGED      # literally any of the above
        }

        if mode.upper() not in _ACCEPTED_MODES:
            raise ValueError(
                f"keyword argument 'mode' must be one of: {_ACCEPTED_MODES}, got '{mode}'"
            )

        if mode == 'ATTRIBUTE' and attribute is None:
            raise TypeError(
                "missing required keyword argument 'attribute', please specify an "
                "attribute to monitor"
            )

        # ...

        checks = [EntityCheck(entity_id=entity_id, domain=domain)]

        if mode in ('CHANGE', 'ATTRIBUTE', 'UPDATE'):
            if from_value or to_value:
                check = DiscreteValueCheck(
                            from_=from_value,
                            to_=to_value,
                            attribute=attribute
                        )
                checks.append(check)

            if above_value or below_value:
                check = ContinuousValueCheck(
                            above=above_value,
                            below=below_value,
                            inclusive=inclusive,
                            attribute=attribute
                        )
                checks.append(check)

            # TODO
            #
            # if len(checks) == 1 and duration:
            #     check = ValueDurationCheck()
            #     checks.append(check)
            #
            # need logic for duration-check
            # - check which delegates, wait, delegates, returns?
            # - subclass of debounce?

        event = _ACCEPTED_MODES[mode]

        try:
            intent_kwargs['checks'].extend(checks)
        except KeyError:
            intent_kwargs['checks'] = checks

        intent = Intent(event, fn=fn, **intent_kwargs)
        return intent
