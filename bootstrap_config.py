# -*- coding: utf-8 -*-


def post_bootstrap(**kwargs):
    from mollusc import venv

    if kwargs['dev']:
        venv.add_path('.')
        venv.add_script('dev', 'dev', 'main')
