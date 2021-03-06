from collections.abc import Iterable

from ward import test, raises

from hautomate.errors import HautoError
from hautomate.app import App
from hautomate import Hautomate

from tests.fixtures import cfg_hauto


@test('AppRegistry implements __len__, __iter__, __getattr__, and .names', tags=['unit'])
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = Hautomate(cfg)
    hauto.apps._load_all_apps(None)

    assert len(hauto.apps) == 3
    assert isinstance(hauto.apps, Iterable) is True
    assert isinstance(hauto.apps.names, list) is True

    for app_name, app in zip(hauto.apps.names, hauto.apps):
        assert getattr(hauto.apps, app_name) == app


@test('AppRegistry warns when no setup() method found', tags=['unit'])
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = Hautomate(cfg)

    with raises(HautoError):
        hauto.apps._invalid_app


@test('AppRegistry errors on non-loaded apps', tags=['unit'])
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = Hautomate(cfg)

    # can't find app
    with raises(HautoError):
        hauto.apps.some_app_that_doesnt_actually_exist_ayy_lmao

    with raises(HautoError):
        hauto.apps._hidden_app


@test('AppRegistry doesn\'t autoload private files', tags=['unit'])
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = Hautomate(cfg)

    # can't find app
    with raises(HautoError):
        hauto.apps.hidden

    hauto.apps._load_all_apps(None)

    # still can't find app!
    with raises(HautoError):
        hauto.apps.hidden

    # ahhh finally
    hauto.apps.load_app('_hidden_app')
    assert isinstance(hauto.apps.hidden, App) is True
    # hauto.apps.load_app('_naughty_app')


@test('AppRegistry won\'t load two apps by the same name', tags=['unit'])
async def _(cfg=cfg_hauto):
    """ async because we call loop.create_task upon AppRegistry.load(app) """
    hauto = Hautomate(cfg)
    apps = hauto.apps.load_app('_hidden_app')

    with raises(HautoError):
        hauto.apps.load_app('_hidden_app')

    for app in apps:
        hauto.apps.unload_app(app.name)

    with raises(HautoError):
        hauto.apps.unload_app('hidden')

    hauto.apps.load_app('_hidden_app')
