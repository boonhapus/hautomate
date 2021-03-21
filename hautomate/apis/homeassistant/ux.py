from typing import List
import logging

from homeassistant.components.input_boolean import InputBoolean as InputBoolean_, InputBooleanStorageCollection
from homeassistant.components.input_select import InputSelect as InputSelect_, InputSelectStorageCollection
from homeassistant.components.input_number import InputNumber as InputNumber_, NumberStorageCollection
from homeassistant.components.input_text import InputText as InputText_, InputTextStorageCollection
from homeassistant.helpers.entity import Entity

from hautomate.apis import homeassistant as hass


_log = logging.getLogger(__name__)


class HautomateEntity:

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

    async def create(self, ctx):
        """
        Associate Hautomate representation with HomeAssistant.
        """
        self.entity = await hass.create_helper(self.entity)

    def __str__(self) -> Entity:
        return self.entity

    @classmethod
    def as_control(cls, *, event='ready', **kw):
        kw['name'] = kw.get('name', 'DEFERRED_TO_SETNAME')

        ins = cls(**kw)
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
    """
    def __init__(self, object_id, options: List[str], **kw):
        kw['options'] = options

        super().__init__(
            InputSelectStorageCollection,
            InputSelect_,
            object_id,
            **kw
        )
