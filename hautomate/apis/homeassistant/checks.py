from homeassistant.core import split_entity_id, valid_entity_id

from hautomate.context import Context
from hautomate.check import Check


class EntityCheck(Check):
    """
    """
    def __init__(self, *, entity_id: str=None, domain: str=None):
        if all((entity_id, domain)):
            raise ValueError(
                "EntityCheck accepts either 'entity_id' or 'domain', but not both. "
            )

        if entity_id is not None and not valid_entity_id(entity_id):
            raise TypeError(
                f'Invalid entity id encountered: {entity_id}. '
                f'Format should be <domain>.<object_id>'
            )

        self.entity_id = entity_id
        self.domain = domain
        super().__init__(concurrency='safe_sync')

    def __check__(self, ctx: Context) -> bool:
        try:
            entity_id = ctx.event_data['entity_id']
        except KeyError:
            return False

        domain, object_id = split_entity_id(entity_id)

        if self.domain is not None:
            return self.domain == domain

        if self.entity_id is not None:
            return self.entity_id == entity_id

        return False
