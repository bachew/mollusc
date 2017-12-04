# -*- coding: utf-8 -*-
import click
import docker
import os
from mollusc import sh
from mollusc.dist import Twine
from os import path as osp


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


@cli.command('deploy-wheel')
@click.option('-u', '--username')
def cli_deploy_wheel(username):
    twine = Twine(username)
    files = sh.glob(sh.path('dist', '*.whl'))
    twine.upload(files)


@cli.command('deploy-doc')
def cli_deploy_doc():
    sh.call(['mkdocs', 'gh-deploy', '--force'])


@cli.command('build-image')
@click.option('--rebuild', is_flag=True, help='Rebuild if base image already exists')
@click.argument('platform', nargs=-1)
def cli_build_image(platform, rebuild):
    docker = Docker()
    test_suffix = '-test'
    platf_names = platform or [n for n in os.listdir('docker') if n.endswith(test_suffix)]

    try:
        for platf_name in platf_names:
            if platf_name.endswith(test_suffix):
                base_platf_name = platf_name[:-len(test_suffix)]
                test_platf_name = platf_name
            else:
                base_platf_name = platf_name
                test_platf_name = None

            if base_platf_name:
                if rebuild:
                    docker.remove_image(base_platf_name)  # TODO: image name

                docker.build_image(base_platf_name)

            if test_platf_name:
                docker.remove_image(test_platf_name)  # TODO: image name
                docker.build_image(test_platf_name, '.')
    finally:
        docker.remove_dangling_images()


class Docker(object):
    IMAGE_PREFIX = 'mollusc-'

    def __init__(self):
        self.docker = docker.from_env()

    def build_image(self, platform_name, path=None):
        image_name = '{}{}'.format(self.IMAGE_PREFIX, platform_name)

        try:
            self.docker.images.get(image_name)
        except docker.errors.ImageNotFound:
            cmd = ['docker', 'build', '-t', image_name, '--network', 'host']

            if path is None:
                cmd.append(sh.path('docker', platform_name))
            else:
                cmd += [
                    '-f', sh.path('docker', platform_name, 'Dockerfile'),
                    path
                ]

            sh.call(cmd)
        else:
            sh.echo('Image {!r} already exists'.format(image_name))

    def remove_dangling_images(self):
        for image in self.docker.images.list(filters={'dangling': True}):
            self.remove_image(image.short_id)

    def remove_image(self, name):
        try:
            self.docker.images.get(name)
        except docker.errors.ImageNotFound:
            sh.echo('Image {!r} does not exist'.format(name))
        else:
            sh.call(['docker', 'image', 'rm', '-f', name])
