from homeassistant.components.input_boolean import InputBoolean, InputBooleanStorageCollection
from homeassistant.components.input_number import InputNumber, InputNumberStorageCollection
from homeassistant.components.input_text import InputText, InputTextStorageCollection
from homeassistant.helpers.entity import Entity


def create_input_text(name, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputTextStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputText.from_yaml(cfg)


def create_input_number(name, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputNumberStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputNumber.from_yaml(cfg)


def create_input_boolean(name, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputBooleanStorageCollection.CREATE_SCHEMA(data)
    cfg['id'] = name
    return InputBoolean(cfg, from_yaml=True)
