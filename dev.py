# -*- coding: utf-8 -*-
import click
import docker
import os
from mollusc import sh
from mollusc.dist import Twine
from os import path as osp


IMAGE_PREFIX = 'mollusc-'


@click.group(chain=True, context_settings={'help_option_names': ['-h', '--help']})
def cli():
    sh.change_dir(osp.dirname(__file__))


class Cli(object):
    @cli.command('test')
    @click.option('-T', '--skip-tox', is_flag=True,
                  help='Skip running tox (not tox in docker tests).')
    @click.option('-D', '--skip-docker', is_flag=True,
                  help='Skip docker tests.')
    @click.option('-i', '--docker-image', multiple=True,
                  help=('Docker image to test on (e.g. debian-jessie),'
                        ' can be spcified multiple times, default all images.'))
    def test(skip_tox, skip_docker, docker_image):
        if not skip_tox:
            sh.remove('.tox')
            sh.call(['tox'])

        if skip_docker:
            return

        if not docker_image:
            docker_image = [n for n in os.listdir('docker')]

        try:
            for image_name in docker_image:
                test_image(image_name)
        finally:
            remove_dangling_images()

    @cli.command('build')
    def build():
        sh.remove(['build', 'dist'])
        sh.remove(sh.glob(sh.path('src', '*.egg.info')))
        sh.call(['python', 'setup.py', 'build', 'bdist_wheel'])

        sh.remove('.site')
        sh.call(['mkdocs', 'build'])

    @cli.command('deploy-wheel')
    @click.option('-u', '--username')
    def deploy_wheel(username):
        twine = Twine(username)
        files = sh.glob(sh.path('dist', '*.whl'))
        twine.upload(files)

    @cli.command('deploy-doc')
    def deploy_doc():
        sh.call(['mkdocs', 'gh-deploy', '--force'])


def test_image(name):
    if name.startswith(IMAGE_PREFIX):
        tag = name
        name = name[len(IMAGE_PREFIX):]
    else:
        tag = IMAGE_PREFIX + name

    sh.call([
        'docker', 'build',
        '-t', tag,
        '--network', 'host',
        sh.path('docker', name)
    ])

    script_name = name + '.sh'
    project_dir = '/tmp/mollusc'

    sh.call([
        'docker', 'run',
        '-v', '{}:{}'.format(sh.path('.', rel=False), project_dir),
        '-w', project_dir,
        '--network', 'host',
        '-t',
        '-a', 'STDIN', '-a', 'STDOUT', '-a', 'STDERR',
        '-e', 'LC_ALL=C.UTF-8',
        '-e', 'LANG=C.UTF-8',
        tag,
        'bash', '-ex', sh.path('docker-test', script_name)
    ])


def remove_dangling_images():
    dock = docker.from_env()

    for image in dock.images.list(filters={'dangling': True}):
        sh.call(['docker', 'image', 'rm', '-f', image.short_id])
