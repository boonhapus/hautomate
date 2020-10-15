from homeassistant.components.input_text import InputBoolean, InputBooleanStorageCollection
from homeassistant.components.input_text import InputText, InputTextStorageCollection
from homeassistant.core import Entity


def create_input_text(name, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputTextStorageCollection.CREATE_SCHEMA(data)
    return InputText.from_yaml(cfg)


def create_input_boolean(name, **data) -> Entity:
    """
    """
    data['name'] = name
    cfg = InputBooleanStorageCollection.CREATE_SCHEMA(data)
    return InputBoolean.from_yaml(cfg)
