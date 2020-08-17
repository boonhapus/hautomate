import json

from ward import test, raises
import pydantic

from hautomate.settings import HautoConfig

from tests.fixtures import cfg_data_hauto


@test('positive scenarios: HAutoConfig')
def _(opts=cfg_data_hauto):
    model = HautoConfig(**opts)

    # remove because comparing relative paths is impossibru
    _opts = {k: v for k, v in opts.items() if k != 'apps_dir'}

    excludes = {f for f in model.fields if f not in _opts}
    model_data = model.json(exclude=excludes)
    assert json.loads(model_data) == _opts


@test('negative scenarios: HAutoConfig')
def _(opts=cfg_data_hauto):
    with raises(pydantic.ValidationError):
        HautoConfig(**{**opts, **{'timezone': 'America/Gotham City'}})

    with raises(pydantic.ValidationError):
        HautoConfig(**{**opts, **{'api_configs': {'time_travel': None}}})
