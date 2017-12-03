# -*- coding: utf-8 -*-
import click
from mollusc import sh
from mollusc.dist import Twine
from os import path as osp


@click.group(chain=True,
             context_settings={'help_option_names': ['-h', '--help']})
def main():
    sh.change_dir(osp.dirname(__file__))


@main.command('test')
def test():
    sh.remove('.tox')
    sh.call(['tox'])


@main.command('build')
def build():
    sh.remove(['build', 'dist'])
    sh.remove(sh.glob(sh.path('src', '*.egg.info')))
    sh.call(['python', 'setup.py', 'build', 'bdist_wheel'])

    sh.remove('.site')
    sh.call(['mkdocs', 'build'])


@main.command('deploy-wheel')
@click.option('-u', '--username')
def deploy_wheel(username):
    twine = Twine(username)
    files = sh.glob(sh.path('dist', '*.whl'))
    twine.upload(files)


@main.command('deploy-doc')
def deploy_doc():
    sh.call(['mkdocs', 'gh-deploy', '--force'])
