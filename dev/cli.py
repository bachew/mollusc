# -*- coding: utf-8 -*-
from __future__ import print_function
import click
from mollusc import sh
from os import path as osp


PROJECT_DIR = sh.abspath(osp.dirname(__file__), '..')
CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help']
}


class BuildFailed(Exception):
    pass


@click.group(context_settings=CONTEXT_SETTINGS)
def main():
    '''
    Build tool for Mollusc.
    '''
    sh.change_dir(PROJECT_DIR)


@main.command('doc')
def doc():
    '''
    Serve doc on localhost for browser preview.
    '''
    sh.call(['mkdocs', 'serve'])
