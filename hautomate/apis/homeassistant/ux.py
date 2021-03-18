from typing import List

from homeassistant.components.input_boolean import InputBoolean, InputBooleanStorageCollection
from homeassistant.components.input_select import InputSelect, InputSelectStorageCollection
from homeassistant.components.input_number import InputNumber, NumberStorageCollection
from homeassistant.components.input_text import InputText, InputTextStorageCollection
from homeassistant.helpers.entity import Entity


def create_input_text(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputTextStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputText.from_yaml(cfg)


def create_input_number(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = NumberStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputNumber.from_yaml(cfg)


def create_input_boolean(name: str, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputBooleanStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputBoolean.from_yaml(cfg)


def create_input_select(name: str, options: List[str], **data) -> Entity:
    """
    """
    data['name'] = name
    data['options'] = options
    cfg = InputSelectStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputSelect.from_yaml(cfg)
