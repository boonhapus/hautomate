import pathlib

from ward import fixture

from hautomate.settings import HautoConfig


@fixture(scope='global')
def cfg_data_hauto():
    opts = {
        'apps_dir': f'{pathlib.Path(__file__).parent}/_test_apps',
        'latitude': 33.05861,
        'longitude': -96.74493,
        'elevation': 214.0,
        'timezone': 'America/Chicago',
        # 'api_configs': {}
    }
    return opts


@fixture(scope='global')
def cfg_hauto(opts=cfg_data_hauto):
    return HautoConfig(**opts)
