from ward import test, each, raises

from homeassistant.core import HomeAssistant
from hautomate.settings import HautoConfig
from hautomate import Hautomate
import pydantic

from tests.fixtures import cfg_data_hauto


@test('HomeAssistantConfig validates for {feed}', tags=['unit'])
async def _(
    cfg_data=cfg_data_hauto,
    feed=each('custom_component', 'custom_component', 'websocket'),
    hass_cls=each(HomeAssistant, None, None)
):
    if hass_cls is not None:
        hass = hass_cls()
    else:
        hass = None

    # overwrite any existing api configs
    data = cfg_data.copy()

    data['api_configs'] = {
        'homeassistant': {
            'feed': feed,
            'hass_interface': hass,
            'host': 'http://hautomate.boonhap.us',
            'port': 8823,
            'access_token': 'damn, granted!'
        }
    }

    if feed == 'custom_component' and hass is None:
        with raises(pydantic.ValidationError):
            cfg = HautoConfig(**data)
    else:
        cfg = HautoConfig(**data)
        hauto = Hautomate(cfg)
        assert hauto.is_running is True
        assert hauto.is_ready is False
