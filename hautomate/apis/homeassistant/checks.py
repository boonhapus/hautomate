from homeassistant.core import split_entity_id, valid_entity_id

from hautomate.context import Context
from hautomate.check import Check


class EntityCheck(Check):
    """
    Check if Entities match via .entity_id or .domain.

    Attributes
    ----------
    entity_id : str
      name of the entity to match

    domain : str, default None
      domain to match against
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


class DiscreteValueCheck(Check):
    """
    """
    def __init__(self, from_: str, to_: str, *, attribute: str=None):
        self.from_ = from_
        self.to_ = to_
        self.attribute = attribute
        super().__init__(concurrency='safe_sync')

    def __check__(self, ctx: Context) -> bool:
        old = ctx.event_data['old_entity']
        new = ctx.event_data['new_entity']

        if self.attribute is not None:
            old_value = old['attributes'].get(self.attribute, 'SENTINEL_NULL')
            new_value = new['attributes'].get(self.attribute, 'SENTINEL_NULL')
        else:
            old_value = old.state
            new_value = new.state

        if self.from_ is not None and self.from_ != old_value:
            return False

        if self.to_ is not None and self.to_ != new_value:
            return False

        return True


class ContinuousValueCheck(Check):
    """
    """
    def __init__(
        self,
        above: float=None,
        below: float=None,
        *,
        inclusive: bool=False,
        attribute: str=None
    ):
        if not any((above, below)):
            raise TypeError("ContinuousStateCheck missing 1 required argument 'above' or 'below'")

        self.above = above
        self.below = below
        self.inclusive = inclusive
        self.attribute = attribute
        super().__init__(concurrency='safe_sync')

    def __check__(self, ctx: Context) -> bool:
        entity = ctx.event_data['new_entity']

        if self.attribute is not None:
            value = entity['attributes'].get(self.attribute, 'SENTINEL_NULL')
        else:
            value = entity.state

        if self.above is not None:
            if self.inclusive and value >= self.above:
                return False
            elif value > self.above:
                return False

        if self.below is not None:
            if self.inclusive and value <= self.below:
                return False
            elif value < self.below:
                return False

        return True
