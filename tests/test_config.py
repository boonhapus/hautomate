from ward import test, fixture, skip


@fixture
def cfg_data_hauto():
    opts = {
        'apps_dir': '../example_apps',
        'latitude': 33.05861,
        'longitude': -96.74493,
        'elevation': 214,
        'timezone': 'America/Chicago',
    }
    return opts


@skip('TODO, testing CI/CD')
@test('hauto configuration')
def _(opts=cfg_data_hauto):
    assert False


@test('testing coverage')
def _(opts=cfg_data_hauto):
    assert True is False
