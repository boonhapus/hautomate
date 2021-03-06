from typing import Dict, List, Any
import logging

from homeassistant.components.input_boolean import InputBoolean as InputBoolean_, InputBooleanStorageCollection
from homeassistant.components.input_select import InputSelect as InputSelect_, InputSelectStorageCollection
from homeassistant.components.input_number import InputNumber as InputNumber_, NumberStorageCollection
from homeassistant.components.input_text import InputText as InputText_, InputTextStorageCollection
from homeassistant.helpers.entity import Entity

from hautomate.apis import homeassistant as hass


_log = logging.getLogger(__name__)


class HautoSensor(Entity):
    """
    ...

    Further Reading:
    https://github.com/home-assistant/core/blob/55b689b4649a7bb916618b70bffa42296bdb41cf/homeassistant/helpers/entity.py#L130-L251
    """
    entity_registry_enabled_default = True
    should_poll = False

    @property
    def state(self):
        return self._state

    @property
    def state_attributes(self):
        return self._state_attributes

    @property
    def icon(self):
        return self._icon

    async def create(self):
        """
        """
        # pls don't look at this mess <:F
        ha = hass.instances[hass.api_name].hass_interface._hass
        platform = ha.data['hautomate']['sensor_platform']
        await platform.async_add_entities([self])

    async def update(self, state: str, attributes: Dict[str, Any]):
        """
        """
        self._state = state
        self._state_attributes = attributes
        self.async_write_ha_state()


class HautomateEntity:
    """
    Wrapper to create a HomeAssistant Helper.
    """

    def __init__(self, collection_cls, hass_entity_cls, object_id, **kw):
        if object_id == 'DEFERRED_TO_SETNAME':
            kw['collection_cls'] = collection_cls
            kw['hass_entity_cls'] = hass_entity_cls
            self._kw = kw
            self.entity = None
            return

        kw['name'] = object_id
        cfg = collection_cls.CREATE_SCHEMA(kw)
        cfg['id'] = object_id
        self.entity = hass_entity_cls.from_yaml(cfg)

    def __set_name__(self, owner, object_id: str):
        if self.entity is not None:
            return

        kw = self._kw.copy()
        collection_cls = kw.pop('collection_cls')
        hass_entity_cls = kw.pop('hass_entity_cls')
        del self._kw

        kw['name'] = object_id
        cfg = collection_cls.CREATE_SCHEMA(kw)
        cfg['id'] = object_id
        self.entity = hass_entity_cls.from_yaml(cfg)

    def __get__(self, instance, type=None):
        return self

    def __set__(self, instance, value):
        _log.error('cannot override this entity')

    async def create(self, *a, **kw):
        """
        Associate Hautomate representation with HomeAssistant.
        """
        self.entity = await hass.create_helper(self.entity)
        return self.entity

    def __str__(self) -> Entity:
        return self.entity

    @classmethod
    def as_control(cls, object_id='DEFERRED_TO_SETNAME', *, event='ready', **kw):
        ins = cls(object_id, **kw)
        ins.__hauto_event__ = event
        setattr(ins, f'on_{event}', ins.create)
        return ins


class InputBoolean(HautomateEntity):
    """
    Hautomate augmentation of the helper InputBoolean.
    """
    def __init__(self, object_id, **kw):
        super().__init__(
            InputBooleanStorageCollection,
            InputBoolean_,
            object_id,
            **kw
        )


class InputText(HautomateEntity):
    """
    Hautomate augmentation of the helper InputText.
    """
    def __init__(self, object_id, **kw):
        super().__init__(
            InputTextStorageCollection,
            InputText_,
            object_id,
            **kw
        )


class InputNumber(HautomateEntity):
    """
    Hautomate augmentation of the helper InputNumber.
    """
    def __init__(self, object_id, **kw):
        super().__init__(
            NumberStorageCollection,
            InputNumber_,
            object_id,
            **kw
        )


class InputSelect(HautomateEntity):
    """
    Hautomate augmentation of the helper InputSelect.
    """
    def __init__(self, object_id, *, options: List[str], **kw):
        kw['options'] = options

        super().__init__(
            InputSelectStorageCollection,
            InputSelect_,
            object_id,
            **kw
        )
