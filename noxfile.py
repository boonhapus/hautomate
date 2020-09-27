import os

import nox


ON_GITHUB = 'GITHUB_ACTIONS' in os.environ

py37 = '3.7.9'
py38 = '3.8'

nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True
nox.options.sessions = [
    'test'
]


@nox.session(python=[py37, py38])
def test(session):
    session.install('-U', '.[test]')
    session.run('coverage', 'run', '-m', 'ward', *session.posargs)
    session.notify('report')


# @nox.session(python=[py36, py37, py38])
# def integration(session):
#     session.install('-U', '.[test]')
#     session.run('coverage', 'run', '-m', 'ward', '--tags', 'integration', *session.posargs)
#     session.notify('report')


# @nox.session(python=[py36, py37, py38])
# def unit(session):
#     session.install('-U', '.[test]')
#     session.run('coverage', 'run', '-m', 'ward', '--tags', 'unit', *session.posargs)
#     session.notify('report')


@nox.session
def report(session):
    session.install('-U', 'coverage[toml]')

    if ON_GITHUB:
        session.run('coverage', 'xml')
    else:
        session.run('coverage', 'report', '-m')
        session.run('coverage', 'erase')
