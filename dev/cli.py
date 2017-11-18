# -*- coding: utf-8 -*-
from __future__ import print_function
import click
from mollusc import sh
from os import path as osp


PROJECT_DIR = sh.abspath(osp.dirname(__file__), '..')
CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help']
}


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    sh.change_dir(PROJECT_DIR)


@main.command('build')
def build():
    for python in ['python', 'python2', 'python2.7', 'python3', 'python3.4', 'python3.5', 'python3.6']:
        try:
            sh.call([python, '--version'])
        except sh.CommandNotFound:
            sh.echo('command not found')
