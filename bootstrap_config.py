# -*- coding: utf-8 -*-
python = 'python'


def post_bootstrap(**kwargs):
    from mollusc import venv

    if kwargs['dev']:
        venv.add_path('dev')
        venv.add_script('dev', 'cli', 'main')
