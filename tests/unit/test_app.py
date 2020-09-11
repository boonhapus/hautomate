from ward import test, raises

from hautomate.errors import HautoError
from hautomate import HAutomate

from tests.fixtures import cfg_hauto


@test('AppRegistry implements len, .items, .names, dict-like member accessor')
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)
    assert len(hauto.apps) == 0

    hauto.apps._initial_load_apps()
    app_names = list(hauto.apps._apps.keys())
    apps = list(hauto.apps._apps.values())
    assert len(app_names) == 2

    for name, app in zip(app_names, apps):
        assert hauto.apps[name] == app

    for v_app, i_app in zip(hauto.apps.values(), hauto.apps):
        assert v_app == i_app

    for k_name, name in zip(hauto.apps.keys(), hauto.apps.names()):
        assert k_name == name

    for i, (k, v) in enumerate(hauto.apps.items()):
        assert k == app_names[i]
        assert v == apps[i]

    with raises(HautoError):
        hauto.apps['nope']


@test('AppRegistry loads and unloads apps')
async def _(cfg=cfg_hauto):
    hauto = HAutomate(cfg)

    for file_obj in hauto.config.apps_dir.iterdir():
        if file_obj.is_file():
            hauto.apps.load_app(file_obj)

    assert len(hauto.apps) == 2

    for name in hauto.apps.names():
        hauto.apps.unload_app(name)

    assert len(hauto.apps) == 0
