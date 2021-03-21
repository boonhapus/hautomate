from typing import List
import logging

from homeassistant.components.input_boolean import InputBoolean as InputBoolean_, InputBooleanStorageCollection
from homeassistant.components.input_select import InputSelect as InputSelect_, InputSelectStorageCollection
from homeassistant.components.input_number import InputNumber as InputNumber_, NumberStorageCollection
from homeassistant.components.input_text import InputText as InputText_, InputTextStorageCollection
from homeassistant.helpers.entity import Entity

from hautomate.apis import homeassistant as hass


_log = logging.getLogger(__name__)


class InputBoolean:

    def __init__(self, name, **kw):
        if name == 'DEFERRED_TO_SETNAME':
            self._kw = kw
            self.entity = None
            return

        kw['name'] = name
        cfg = InputBooleanStorageCollection.CREATE_SCHEMA(kw)
        cfg['id'] = name
        self.entity = InputBoolean_.from_yaml(cfg)

    def __set_name__(self, owner, name):
        if self.entity is not None:
            return

        kw = self._kw.copy()
        del self._kw

        kw['name'] = name
        cfg = InputBooleanStorageCollection.CREATE_SCHEMA(kw)
        cfg['id'] = name
        self.entity = InputBoolean_.from_yaml(cfg)

    def __get__(self, instance, type=None):
        return self

    def __set__(self, instance, value):
        _log.error('cannot override this entity')

    async def create(self, ctx):
        """
        """
        self.entity = await hass.create_helper(self.entity)

    def __str__(self):
        return f'{self.entity}'

    @classmethod
    def as_control(cls, *, event='ready', **kw):
        kw['name'] = kw.get('name', 'DEFERRED_TO_SETNAME')

        ins = cls(**kw)
        ins.__hauto_event__ = event
        setattr(ins, f'on_{event}', ins.create)
        return ins


def create_input_text(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputTextStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputText_.from_yaml(cfg)


def create_input_number(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = NumberStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputNumber_.from_yaml(cfg)


def create_input_boolean(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputBooleanStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputBoolean_.from_yaml(cfg)


def create_input_select(name: str, options: List[str], **data) -> Entity:
    """
    """
    data['name'] = name
    data['options'] = options
    cfg = InputSelectStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputSelect_.from_yaml(cfg)
