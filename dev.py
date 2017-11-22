# -*- coding: utf-8 -*-
import click
import getpass
from click import ClickException
from mollusc import sh
from os import path as osp
from subprocess import list2cmdline


@click.group(context_settings={'help_option_names': ['-h', '--help']})
def main():
    sh.change_dir(osp.dirname(__file__))


@main.command('build')
@click.option('--deploy', is_flag=True)
@click.option('-u', '--username', help='Username for uploading wheel')
def build(deploy, username):
    '''
    Test, build and deploy everything.
    '''
    if not username:
        username = getpass.getuser()

    sh.call(['tox'])

    sh.remove(['build', 'dist'])
    sh.remove(sh.glob('src/*.egg.info'))
    sh.call(['python', 'setup.py', 'build', 'bdist_wheel'])

    if deploy:
        upload_wheel(username)

    sh.call(['mkdocs', 'build'])

    if deploy:
        sh.call(['mkdocs', 'gh-deploy'])


def upload_wheel(username):
    repo_url = 'https://upload.pypi.org/legacy/'

    try:
        sh.output(['keyring', 'get', repo_url, username])
    except sh.CommandFailed:
        cmdline = list2cmdline(['keyring', 'set', repo_url, username])
        raise ClickException('Credentials not found in keyring, you can add by running:\n  {}'.format(cmdline))

    cmd = [
        'twine', 'upload',
        '--repository-url', repo_url,
        '-u', username,
    ]
    cmd += sh.glob('dist/*.whl')
    sh.call(cmd)
