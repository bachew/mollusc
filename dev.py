# -*- coding: utf-8 -*-
import click
import docker
from mollusc import sh
from mollusc.dist import Twine
from os import path as osp
from textwrap import dedent


@click.group(chain=True,
             context_settings={'help_option_names': ['-h', '--help']})
def cli():
    sh.change_dir(osp.dirname(__file__))


@cli.command('test')
def cli_test():
    sh.remove('.tox')
    sh.call(['tox'])


@cli.command('build')
def cli_build():
    sh.remove(['build', 'dist'])
    sh.remove(sh.glob(sh.path('src', '*.egg.info')))
    sh.call(['python', 'setup.py', 'build', 'bdist_wheel'])

    sh.remove('.site')
    sh.call(['mkdocs', 'build'])


@cli.command('docker')
def cli_docker():
    platforms = Platforms()
    platforms.build_all()


@cli.command('deploy-wheel')
@click.option('-u', '--username')
def cli_deploy_wheel(username):
    twine = Twine(username)
    files = sh.glob(sh.path('dist', '*.whl'))
    twine.upload(files)


@cli.command('deploy-doc')
def cli_deploy_doc():
    sh.call(['mkdocs', 'gh-deploy', '--force'])


class Platforms(object):
    def __init__(self):
        self.all = [
            Debian('stable')
        ]
        self.docker = docker.from_env()

    def build_all(self):
        for platform in self.all:
            self.build(platform)

    def build(self, platform):
        self.build_image(platform)
        platform.build()

    def build_image(self, platform):
        images = self.docker.images
        image_name = platform.image_name

        try:
            images.get(image_name)
        except docker.errors.ImageNotFound:
            pass
        else:
            sh.echo('Removing image {!r}'.format(image_name))
            images.remove(image_name, force=True)

        dockerfiles_dir = sh.ensure_dir('.dockerfiles')
        dockerfile_path = sh.path(dockerfiles_dir, image_name)
        sh.write(dockerfile_path, platform.dockerfile)

        # Using CLI instead of API for rich output
        sh.call(['docker', 'build', '-t', image_name, '-f', dockerfile_path, '.'])


class Platform(object):
    def __init__(self, repo, tag):
        self.repo = repo
        self.tag = tag

    @property
    def image_name(self):
        return 'mollusc-{}-{}'.format(self.repo, self.tag)

    @property
    def dockerfile(self):
        return dedent('''\
            FROM {}:{}
            WORKDIR /mollusc
            ADD . /mollusc
            '''.format(self.repo, self.tag))

    def run(self, cmd):
        sh.call(['docker', 'run', self.image_name] + list(cmd))

    def build(self):
        # TODO: can only be one command
        self.run(['/mollusc/bootstrap', 'dev', 'test'])


class Debian(Platform):
    def __init__(self, tag):
        super(Debian, self).__init__('debian', tag)

    def build(self):
        self.run(['bash', '-c', 'apt-get -q update && apt-get -qy install python2.7 python3'])
        super(Debian, self).build()
