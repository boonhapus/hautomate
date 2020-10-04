
HASS_EVENT_RECEIVE = 'HASS_EVENT_RECEIVE'  # hass.bus --> hauto.bus
HASS_STATE_CHANGED = 'HASS_STATE_CHANGE'   # aka hass.EVENT_STATE_CHANGED
HASS_ENTITY_CREATE = 'HASS_ENTITY_CREATE'  # hass entity is newly created
HASS_ENTITY_CHANGE = 'HASS_ENTITY_UPDATE'  # hass entity's state changes
HASS_ENTITY_UPDATE = 'HASS_ENTITY_UPDATE'  # hass entity's state is same, but attributes change
HASS_ENTITY_REMOVE = 'HASS_ENTITY_REMOVE'  # hass entity is removed
