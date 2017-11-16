# -*- coding: utf-8 -*-
def post_bootstrap(**kwargs):
    from mollusc import venv

    venv.add_path('dev')
    venv.add_script('d', 'cli', 'main')
